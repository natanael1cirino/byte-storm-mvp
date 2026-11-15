from django.contrib import admin

from .models import Categoria, ItemPedido, Pedido, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nome", "slug", "ativa"]
    prepopulated_fields = {"slug": ["nome"]}


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "preco", "quantidade_estoque", "esgotado", "ativo"]
    list_filter = ["categoria", "ativo", "esgotado"]
    search_fields = ["nome"]


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ["produto", "quantidade", "preco_unitario"]
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "cliente_nome", "status", "valor_total", "criado_em"]
    list_filter = ["status", "forma_pagamento"]
    inlines = [ItemPedidoInline]
    readonly_fields = ["valor_total", "registrado_por"]
