"""Camada de serviço: concentra as regras de negócio do MVP.

As views só validam a entrada e chamam estas funções. Assim, a regra de estoque
fica em um único lugar, testável sem abrir nenhuma tela.
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum

from .models import ItemPedido, Pedido, Produto


class EstoqueInsuficiente(Exception):
    """Levantada quando a quantidade pedida é maior que o estoque disponível."""

    def __init__(self, produto, disponivel, pedida):
        self.produto = produto
        self.disponivel = disponivel
        self.pedida = pedida
        super().__init__(
            f"Estoque insuficiente de {produto.nome}: há {disponivel} unidade(s) e foram pedidas {pedida}."
        )


class TransicaoInvalida(Exception):
    """Levantada quando a mudança de status não segue o fluxo permitido."""


@dataclass
class ItemSolicitado:
    produto_id: int
    quantidade: int


# Fluxo de status (RF06): novo → pago → em entrega → entregue; cancelamento antes da entrega.
TRANSICOES = {
    Pedido.Status.NOVO: {Pedido.Status.PAGO, Pedido.Status.CANCELADO},
    Pedido.Status.PAGO: {Pedido.Status.EM_ENTREGA, Pedido.Status.CANCELADO},
    Pedido.Status.EM_ENTREGA: {Pedido.Status.ENTREGUE, Pedido.Status.CANCELADO},
    Pedido.Status.ENTREGUE: set(),
    Pedido.Status.CANCELADO: set(),
}

# Dinheiro e cartão são cobrados na entrega: só esses pedidos podem sair sem estar pagos.
PAGAMENTO_NA_ENTREGA = {Pedido.FormaPagamento.DINHEIRO, Pedido.FormaPagamento.CARTAO}


def transicoes_permitidas(pedido):
    """Status para os quais o pedido pode ir agora.

    Pedidos por Pix precisam estar pagos antes de sair para entrega; pedidos
    em dinheiro ou cartão podem sair direto, pois o pagamento acontece na entrega.
    """
    permitidas = set(TRANSICOES.get(pedido.status, set()))
    if pedido.status == Pedido.Status.NOVO and pedido.forma_pagamento in PAGAMENTO_NA_ENTREGA:
        permitidas.add(Pedido.Status.EM_ENTREGA)
    return permitidas


def registrar_pedido(*, usuario, cliente_nome, cliente_telefone, forma_pagamento, itens,
                     endereco_entrega="", observacao=""):
    """Registra um pedido e dá baixa no estoque na mesma transação (RF04).

    Trava as linhas dos produtos (select_for_update) para que dois pedidos
    simultâneos não vendam a mesma última unidade. Se qualquer item não tiver
    estoque suficiente, nada é gravado.

    Returns:
        Pedido: o pedido criado, com status Novo.

    Raises:
        EstoqueInsuficiente: se algum item exceder o estoque disponível.
        ValueError: se não houver itens ou houver quantidade inválida.
    """
    if not itens:
        raise ValueError("O pedido precisa de pelo menos um item.")

    quantidades = defaultdict(int)
    for item in itens:
        if item.quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")
        quantidades[item.produto_id] += item.quantidade

    with transaction.atomic():
        produtos = {
            p.pk: p
            for p in Produto.objects.select_for_update().filter(pk__in=quantidades.keys(), ativo=True)
        }
        if len(produtos) != len(quantidades):
            raise ValueError("Produto inexistente ou inativo no pedido.")

        for produto_id, quantidade in quantidades.items():
            produto = produtos[produto_id]
            if quantidade > produto.quantidade_estoque:
                raise EstoqueInsuficiente(produto, produto.quantidade_estoque, quantidade)

        pedido = Pedido.objects.create(
            cliente_nome=cliente_nome.strip(),
            cliente_telefone=cliente_telefone.strip(),
            endereco_entrega=endereco_entrega.strip(),
            forma_pagamento=forma_pagamento,
            observacao=observacao.strip(),
            registrado_por=usuario,
        )

        total = Decimal("0")
        for produto_id, quantidade in quantidades.items():
            produto = produtos[produto_id]
            ItemPedido.objects.create(
                pedido=pedido, produto=produto, quantidade=quantidade, preco_unitario=produto.preco
            )
            total += produto.preco * quantidade
            produto.quantidade_estoque -= quantidade
            produto.save(update_fields=["quantidade_estoque", "atualizado_em"])

        pedido.valor_total = total
        pedido.save(update_fields=["valor_total"])
    return pedido


def alterar_status(pedido, novo_status):
    """Muda o status do pedido seguindo o fluxo permitido (RF06).

    No cancelamento, as quantidades dos itens voltam ao estoque e o produto
    deixa de estar esgotado, se for o caso.
    """
    if novo_status not in transicoes_permitidas(pedido):
        raise TransicaoInvalida(
            f"Não é possível mudar de {pedido.get_status_display()} para {Pedido.Status(novo_status).label}."
        )

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
        if novo_status not in transicoes_permitidas(pedido):
            raise TransicaoInvalida("O status do pedido foi alterado por outra pessoa. Atualize a página.")
        if novo_status == Pedido.Status.CANCELADO:
            for item in pedido.itens.select_related("produto"):
                # A linha do produto está travada; somar em Python é seguro aqui.
                produto = Produto.objects.select_for_update().get(pk=item.produto_id)
                produto.quantidade_estoque += item.quantidade
                produto.save(update_fields=["quantidade_estoque", "atualizado_em"])
        pedido.status = novo_status
        pedido.save(update_fields=["status", "atualizado_em"])
    return pedido


def relatorio_mensal(ano, mes, limite=5):
    """Faturamento dos pedidos entregues no mês e os produtos mais vendidos (RF07)."""
    pedidos = Pedido.objects.filter(status=Pedido.Status.ENTREGUE, criado_em__year=ano, criado_em__month=mes)
    faturamento = pedidos.aggregate(total=Sum("valor_total"))["total"] or Decimal("0")
    mais_vendidos = (
        ItemPedido.objects.filter(pedido__in=pedidos)
        .values("produto_id", "produto__nome")  # agrupa pelo id: nomes iguais não se misturam
        .annotate(unidades=Sum("quantidade"), valor=Sum(F("quantidade") * F("preco_unitario")))
        .order_by("-unidades", "produto__nome", "produto_id")[:limite]
    )
    return {
        "faturamento": faturamento,
        "quantidade_pedidos": pedidos.count(),
        "mais_vendidos": list(mais_vendidos),
    }
