"""Testes de segurança (RNF01 e RNF02)."""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from loja.models import Pedido, Produto

from .conftest import SENHA_TESTE

ROTAS_DO_PAINEL = [
    "loja:painel", "loja:produtos", "loja:produto_novo", "loja:pedidos", "loja:novo_pedido", "loja:relatorio",
]


@pytest.mark.django_db
@pytest.mark.parametrize("rota", ROTAS_DO_PAINEL)
def test_painel_exige_login(client, rota):
    resposta = client.get(reverse(rota))
    assert resposta.status_code == 302
    assert reverse("loja:login") in resposta.url


@pytest.mark.django_db
def test_senha_armazenada_somente_como_hash_pbkdf2(socio):
    senha_no_banco = get_user_model().objects.get(pk=socio.pk).password
    assert senha_no_banco.startswith("pbkdf2_sha256$")
    assert SENHA_TESTE not in senha_no_banco


@pytest.mark.django_db
def test_bloqueio_apos_cinco_tentativas(client, socio):
    for _ in range(5):
        client.post(reverse("loja:login"), {"username": "socio", "password": "errada"})
    resposta = client.post(reverse("loja:login"), {"username": "socio", "password": SENHA_TESTE})
    assert resposta.status_code == 429
    assert "Muitas tentativas" in resposta.content.decode()


@pytest.mark.django_db
def test_logout_encerra_a_sessao(client, socio):
    client.post(reverse("loja:login"), {"username": "socio", "password": SENHA_TESTE})
    assert client.get(reverse("loja:painel")).status_code == 200
    client.post(reverse("loja:logout"))
    assert client.get(reverse("loja:painel")).status_code == 302


@pytest.mark.django_db
def test_post_sem_token_csrf_e_recusado(socio, fone):
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(socio)
    resposta = cliente.post(reverse("loja:produto_editar", args=[fone.pk]), {"nome": "Alterado"})
    assert resposta.status_code == 403


@pytest.mark.django_db
def test_nome_com_script_e_escapado_no_catalogo(client, categoria):
    Produto.objects.create(nome="<script>alert(1)</script>", preco="10.00", quantidade_estoque=1, categoria=categoria)
    html = client.get(reverse("loja:catalogo")).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.django_db
def test_busca_com_injecao_sql_nao_quebra(client, fone):
    resposta = client.get(reverse("loja:catalogo"), {"q": "' OR 1=1; DROP TABLE loja_produto; --"})
    assert resposta.status_code == 200
    assert Produto.objects.filter(pk=fone.pk).exists()


@pytest.mark.django_db
def test_cabecalho_csp_presente(client):
    resposta = client.get(reverse("loja:catalogo"))
    assert "script-src 'self'" in resposta["Content-Security-Policy"]


@pytest.mark.django_db
def test_catalogo_nao_expoe_dados_de_pedidos(client, socio, fone):
    Pedido.objects.create(cliente_nome="Cliente Sigiloso", cliente_telefone="35999990000",
                          forma_pagamento="pix", registrado_por=socio)
    html = client.get(reverse("loja:catalogo")).content.decode()
    assert "Cliente Sigiloso" not in html
