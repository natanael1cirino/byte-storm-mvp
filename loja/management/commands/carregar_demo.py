"""Carrega dados FICTÍCIOS de demonstração (categorias, produtos e um usuário de teste).

Uso: python manage.py carregar_demo
A senha do usuário de teste é lida da variável DEMO_SENHA; nunca use em produção.
"""
import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from loja.models import Categoria, Produto

PRODUTOS = [
    ("Fones", "fones", "Fone Bluetooth TWS X10", "89.90", 5),
    ("Fones", "fones", "Fone com fio P2 Básico", "29.90", 12),
    ("Carregadores", "carregadores", "Carregador Turbo USB-C 20W", "49.90", 0),
    ("Carregadores", "carregadores", "Carregador veicular duplo", "39.90", 7),
    ("Cabos", "cabos", "Cabo USB-C 1 m reforçado", "24.90", 20),
    ("Cabos", "cabos", "Cabo Lightning 1 m", "34.90", 3),
    ("Caixas de som", "caixas-de-som", "Caixa de som portátil Mini", "129.90", 2),
    ("Acessórios", "acessorios", "Suporte veicular magnético", "44.90", 6),
]


class Command(BaseCommand):
    help = "Carrega produtos fictícios e um usuário de teste para demonstração."

    def handle(self, *args, **options):
        for cat_nome, slug, nome, preco, estoque in PRODUTOS:
            categoria, _ = Categoria.objects.get_or_create(slug=slug, defaults={"nome": cat_nome})
            Produto.objects.update_or_create(
                nome=nome,
                defaults={"categoria": categoria, "preco": Decimal(preco), "quantidade_estoque": estoque},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(PRODUTOS)} produtos fictícios carregados."))

        senha = os.environ.get("DEMO_SENHA")
        if not senha:
            raise CommandError("Defina DEMO_SENHA para criar o usuário de teste 'socio.teste'.")
        User = get_user_model()
        usuario, _ = User.objects.get_or_create(username="socio.teste", defaults={"first_name": "Sócio Teste"})
        usuario.set_password(senha)
        usuario.save()
        self.stdout.write(self.style.SUCCESS("Usuário de teste 'socio.teste' pronto."))
