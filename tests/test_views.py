"""Testes das telas: catálogo público, novo pedido e alertas (RF02, RF03, RF04, RF08)."""
import pytest
from django.urls import reverse

from loja.models import Pedido, Produto


@pytest.mark.django_db
def test_catalogo_publico_mostra_disponivel_e_esgotado(client, fone, categoria):
    Produto.objects.create(nome="Carregador Turbo USB-C 20W", preco="49.90", quantidade_estoque=0, categoria=categoria)

    resposta = client.get(reverse("loja:catalogo"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Fone Bluetooth TWS X10" in html
    assert "✔ Disponível" in html
    assert "✖ Esgotado" in html
    assert html.count("Comprar pelo WhatsApp") == 1  # só o produto disponível tem botão


@pytest.mark.django_db
def test_botao_whatsapp_leva_nome_e_preco(client, fone):
    html = client.get(reverse("loja:catalogo")).content.decode()
    assert "https://wa.me/" in html
    assert "Fone%20Bluetooth%20TWS%20X10" in html
    assert "R%24%2089%2C90" in html


@pytest.mark.django_db
def test_catalogo_esconde_inativos_e_filtra_busca(client, fone, caixa_som):
    Produto.objects.filter(pk=caixa_som.pk).update(ativo=False)
    html = client.get(reverse("loja:catalogo"), {"q": "caixa"}).content.decode()
    assert "Caixa de som" not in html
    assert "Nenhum produto encontrado" in html


@pytest.mark.django_db
def test_novo_pedido_redireciona_para_confirmacao(cliente_logado, fone):
    resposta = cliente_logado.post(reverse("loja:novo_pedido"), {
        "produto": fone.pk, "quantidade": 2, "cliente_nome": "Maria Exemplo",
        "cliente_telefone": "(35) 90000-0001", "endereco_entrega": "Rua Fictícia, 100", "forma_pagamento": "pix",
    }, follow=True)
    html = resposta.content.decode()

    assert "Pedido registrado" in html
    assert "5 → 3 unidades" in html
    assert Pedido.objects.count() == 1


@pytest.mark.django_db
def test_novo_pedido_sem_estoque_mostra_alerta_e_nao_salva(cliente_logado, caixa_som):
    resposta = cliente_logado.post(reverse("loja:novo_pedido"), {
        "produto": caixa_som.pk, "quantidade": 3, "cliente_nome": "João Teste",
        "cliente_telefone": "(35) 90000-0002", "forma_pagamento": "dinheiro",
    })
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "Estoque insuficiente" in html
    assert "informe até 2" in html
    assert Pedido.objects.count() == 0


@pytest.mark.django_db
def test_campos_obrigatorios_tem_rotulo_e_mensagem(cliente_logado, fone):
    resposta = cliente_logado.post(reverse("loja:novo_pedido"), {"produto": fone.pk, "quantidade": 1})
    html = resposta.content.decode()
    assert '<label for="id_cliente_nome">' in html
    assert "Este campo é obrigatório" in html
