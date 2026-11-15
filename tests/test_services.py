"""Testes das regras de negócio da camada de serviço (RF04, RF05, RF06, RF07)."""
from decimal import Decimal

import pytest
from django.utils import timezone

from loja import services
from loja.models import Pedido, Produto
from loja.services import ItemSolicitado


def registrar(socio, itens, **extra):
    dados = {"usuario": socio, "cliente_nome": "Maria Exemplo", "cliente_telefone": "(35) 90000-0001",
             "forma_pagamento": Pedido.FormaPagamento.PIX, "itens": itens}
    dados.update(extra)
    return services.registrar_pedido(**dados)


@pytest.mark.django_db
def test_registrar_pedido_da_baixa_no_estoque_e_calcula_total(socio, fone):
    pedido = registrar(socio, [ItemSolicitado(fone.pk, 2)])

    fone.refresh_from_db()
    assert fone.quantidade_estoque == 3
    assert pedido.status == Pedido.Status.NOVO
    assert pedido.valor_total == Decimal("179.80")
    assert pedido.itens.get().preco_unitario == Decimal("89.90")


@pytest.mark.django_db
def test_pedido_maior_que_estoque_nao_grava_nada(socio, caixa_som):
    with pytest.raises(services.EstoqueInsuficiente) as erro:
        registrar(socio, [ItemSolicitado(caixa_som.pk, 3)])

    caixa_som.refresh_from_db()
    assert erro.value.disponivel == 2
    assert caixa_som.quantidade_estoque == 2
    assert Pedido.objects.count() == 0


@pytest.mark.django_db
def test_pedido_com_varios_itens_e_atomico(socio, fone, caixa_som):
    with pytest.raises(services.EstoqueInsuficiente):
        registrar(socio, [ItemSolicitado(fone.pk, 1), ItemSolicitado(caixa_som.pk, 5)])

    fone.refresh_from_db()
    assert fone.quantidade_estoque == 5  # o primeiro item também não foi baixado
    assert Pedido.objects.count() == 0


@pytest.mark.django_db
def test_ultima_unidade_marca_produto_como_esgotado(socio, caixa_som):
    registrar(socio, [ItemSolicitado(caixa_som.pk, 2)])

    caixa_som.refresh_from_db()
    assert caixa_som.quantidade_estoque == 0
    assert caixa_som.esgotado is True


@pytest.mark.django_db
def test_reposicao_desmarca_esgotado(caixa_som):
    caixa_som.quantidade_estoque = 0
    caixa_som.save()
    assert caixa_som.esgotado is True

    caixa_som.quantidade_estoque = 4
    caixa_som.save()
    caixa_som.refresh_from_db()
    assert caixa_som.esgotado is False


@pytest.mark.django_db
def test_cancelamento_devolve_estoque(socio, caixa_som):
    pedido = registrar(socio, [ItemSolicitado(caixa_som.pk, 2)])

    services.alterar_status(pedido, Pedido.Status.CANCELADO)

    caixa_som.refresh_from_db()
    pedido.refresh_from_db()
    assert pedido.status == Pedido.Status.CANCELADO
    assert caixa_som.quantidade_estoque == 2
    assert caixa_som.esgotado is False


@pytest.mark.django_db
def test_status_segue_fluxo_e_bloqueia_retrocesso(socio, fone):
    pedido = registrar(socio, [ItemSolicitado(fone.pk, 1)])
    for status in (Pedido.Status.PAGO, Pedido.Status.EM_ENTREGA, Pedido.Status.ENTREGUE):
        pedido = services.alterar_status(pedido, status)

    with pytest.raises(services.TransicaoInvalida):
        services.alterar_status(pedido, Pedido.Status.CANCELADO)


@pytest.mark.django_db
def test_pedido_pix_precisa_estar_pago_antes_da_entrega(socio, fone):
    pedido = registrar(socio, [ItemSolicitado(fone.pk, 1)])  # forma de pagamento: Pix

    with pytest.raises(services.TransicaoInvalida):
        services.alterar_status(pedido, Pedido.Status.EM_ENTREGA)


@pytest.mark.django_db
def test_pedido_em_dinheiro_pode_sair_para_entrega_sem_estar_pago(socio, fone):
    pedido = registrar(socio, [ItemSolicitado(fone.pk, 1)], forma_pagamento=Pedido.FormaPagamento.DINHEIRO)

    pedido = services.alterar_status(pedido, Pedido.Status.EM_ENTREGA)

    assert pedido.status == Pedido.Status.EM_ENTREGA


@pytest.mark.django_db
def test_relatorio_nao_mistura_produtos_com_mesmo_nome(socio, categoria):
    a = Produto.objects.create(nome="Cabo USB-C", preco=Decimal("20.00"), quantidade_estoque=5, categoria=categoria)
    b = Produto.objects.create(nome="Cabo USB-C", preco=Decimal("30.00"), quantidade_estoque=5, categoria=categoria)
    for produto, qtd in ((a, 2), (b, 1)):
        pedido = registrar(socio, [ItemSolicitado(produto.pk, qtd)])
        for status in (Pedido.Status.PAGO, Pedido.Status.EM_ENTREGA, Pedido.Status.ENTREGUE):
            pedido = services.alterar_status(pedido, status)

    hoje = timezone.localdate()
    linhas = services.relatorio_mensal(hoje.year, hoje.month)["mais_vendidos"]

    assert len(linhas) == 2
    assert [linha["unidades"] for linha in linhas] == [2, 1]


@pytest.mark.django_db
def test_pedido_sem_itens_e_recusado(socio):
    with pytest.raises(ValueError):
        registrar(socio, [])


@pytest.mark.django_db
def test_produto_inativo_nao_pode_ser_vendido(socio, fone):
    Produto.objects.filter(pk=fone.pk).update(ativo=False)
    with pytest.raises(ValueError):
        registrar(socio, [ItemSolicitado(fone.pk, 1)])


@pytest.mark.django_db
def test_relatorio_considera_apenas_entregues(socio, fone, caixa_som):
    entregue = registrar(socio, [ItemSolicitado(fone.pk, 2)])
    for status in (Pedido.Status.PAGO, Pedido.Status.EM_ENTREGA, Pedido.Status.ENTREGUE):
        entregue = services.alterar_status(entregue, status)
    registrar(socio, [ItemSolicitado(caixa_som.pk, 1)])  # continua "novo", fora do relatório

    hoje = timezone.localdate()
    dados = services.relatorio_mensal(hoje.year, hoje.month)

    assert dados["faturamento"] == Decimal("179.80")
    assert dados["quantidade_pedidos"] == 1
    assert dados["mais_vendidos"][0]["produto__nome"] == "Fone Bluetooth TWS X10"
    assert dados["mais_vendidos"][0]["unidades"] == 2
