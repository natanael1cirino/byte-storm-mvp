"""Modelos do MVP: Categoria, Produto, Pedido e ItemPedido.

O usuário (sócio) vem do módulo de autenticação do Django.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Categoria(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ProdutoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Produto(models.Model):
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quantidade_estoque = models.PositiveIntegerField(default=0)
    foto = models.ImageField(upload_to="produtos/", blank=True)
    esgotado = models.BooleanField(default=True, editable=False)
    ativo = models.BooleanField(default=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="produtos")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = ProdutoQuerySet.as_manager()

    class Meta:
        ordering = ["nome"]
        indexes = [models.Index(fields=["ativo", "categoria"])]
        constraints = [
            models.CheckConstraint(condition=Q(preco__gt=0), name="produto_preco_positivo"),
        ]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # RF05: o produto fica esgotado automaticamente quando o estoque chega a zero.
        self.esgotado = self.quantidade_estoque == 0
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "quantidade_estoque" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {"esgotado"}
        super().save(*args, **kwargs)


class Pedido(models.Model):
    class Status(models.TextChoices):
        NOVO = "novo", "Novo"
        PAGO = "pago", "Pago"
        EM_ENTREGA = "em_entrega", "Em entrega"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    class FormaPagamento(models.TextChoices):
        PIX = "pix", "Pix"
        DINHEIRO = "dinheiro", "Dinheiro"
        CARTAO = "cartao", "Cartão"

    cliente_nome = models.CharField(max_length=100)
    # Opcional desde a 1ª validação: vendas no balcão não têm telefone.
    cliente_telefone = models.CharField(max_length=20, blank=True)
    endereco_entrega = models.CharField(max_length=255, blank=True)
    forma_pagamento = models.CharField(max_length=10, choices=FormaPagamento.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NOVO)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    observacao = models.CharField(max_length=255, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos_registrados"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido nº {self.pk:04d}" if self.pk else "Pedido (novo)"

    @property
    def numero(self):
        return f"{self.pk:04d}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="itens_pedido")
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pedido", "produto"], name="item_unico_por_pedido"),
            models.CheckConstraint(condition=Q(quantidade__gt=0), name="item_quantidade_positiva"),
        ]

    def __str__(self):
        return f"{self.quantidade} × {self.produto}"

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
