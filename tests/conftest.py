from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from loja.models import Categoria, Produto

SENHA_TESTE = "senha-de-teste-123"


@pytest.fixture(autouse=True)
def limpar_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def socio(db):
    return get_user_model().objects.create_user("socio", password=SENHA_TESTE, first_name="Sócio")


@pytest.fixture
def cliente_logado(client, socio):
    client.force_login(socio)
    return client


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Fones", slug="fones")


@pytest.fixture
def fone(categoria):
    return Produto.objects.create(nome="Fone Bluetooth TWS X10", preco=Decimal("89.90"),
                                  quantidade_estoque=5, categoria=categoria)


@pytest.fixture
def caixa_som(categoria):
    return Produto.objects.create(nome="Caixa de som portátil Mini", preco=Decimal("129.90"),
                                  quantidade_estoque=2, categoria=categoria)
