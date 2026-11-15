"""Testes das melhorias pedidas na 1ª rodada de validação com o sócio da Byte Storm."""
import pytest
from django.urls import reverse

from loja.models import Pedido, Produto

DADOS_PEDIDO = {"cliente_nome": "Cliente balcão", "forma_pagamento": "dinheiro"}


@pytest.mark.django_db
def test_pedido_de_balcao_sem_telefone_e_aceito(cliente_logado, fone):
    resposta = cliente_logado.post(reverse("loja:novo_pedido"),
                                   {**DADOS_PEDIDO, "produto": fone.pk, "quantidade": 1}, follow=True)
    html = resposta.content.decode()

    assert "Pedido registrado" in html
    assert "Não informado (balcão)" in html
    assert Pedido.objects.get().cliente_telefone == ""


@pytest.mark.django_db
def test_detalhe_oferece_resumo_no_whatsapp_do_cliente(cliente_logado, fone):
    cliente_logado.post(reverse("loja:novo_pedido"), {
        "produto": fone.pk, "quantidade": 2, "cliente_nome": "Maria Exemplo",
        "cliente_telefone": "(35) 90000-0001", "forma_pagamento": "pix",
    })
    pedido = Pedido.objects.get()
    html = cliente_logado.get(reverse("loja:pedido_detalhe", args=[pedido.pk])).content.decode()

    assert "Enviar resumo ao cliente no WhatsApp" in html
    assert "https://wa.me/5535900000001?text=" in html


@pytest.mark.django_db
def test_detalhe_sem_telefone_nao_mostra_botao_do_cliente(cliente_logado, fone):
    cliente_logado.post(reverse("loja:novo_pedido"), {**DADOS_PEDIDO, "produto": fone.pk, "quantidade": 1})
    pedido = Pedido.objects.get()
    html = cliente_logado.get(reverse("loja:pedido_detalhe", args=[pedido.pk])).content.decode()
    assert "Enviar resumo ao cliente" not in html


@pytest.mark.django_db
def test_catalogo_mostra_quantidade_e_alerta_de_ultimas_unidades(client, fone, caixa_som):
    html = client.get(reverse("loja:catalogo")).content.decode()
    assert "✔ Disponível · 5 un." in html
    assert "⚠ Últimas 2 unidades" in html


@pytest.mark.django_db
def test_catalogo_sem_foto_indica_foto_em_breve(client, fone):
    html = client.get(reverse("loja:catalogo")).content.decode()
    assert "Foto em breve" in html


@pytest.mark.django_db
def test_seletor_de_produto_informa_estoque_para_travar_quantidade(cliente_logado, fone):
    html = cliente_logado.get(reverse("loja:novo_pedido")).content.decode()
    assert 'data-controla-quantidade="id_quantidade"' in html
    assert 'data-estoque="5"' in html


@pytest.mark.django_db
def test_erro_de_estoque_preserva_dados_digitados(cliente_logado, caixa_som):
    resposta = cliente_logado.post(reverse("loja:novo_pedido"), {
        "produto": caixa_som.pk, "quantidade": 3, "cliente_nome": "João Teste",
        "cliente_telefone": "(35) 90000-0002", "forma_pagamento": "dinheiro",
    })
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert 'value="João Teste"' in html
    assert 'value="(35) 90000-0002"' in html
    assert Produto.objects.get(pk=caixa_som.pk).quantidade_estoque == 2
