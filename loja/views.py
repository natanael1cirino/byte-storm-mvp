"""Views do catálogo público e do painel administrativo.

As views validam a entrada e delegam as regras para loja.services.
"""
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import NovoPedidoForm, ProdutoForm, StatusForm
from .models import Categoria, Pedido, Produto

ITENS_POR_PAGINA = 20


def link_whatsapp(produto):
    """Monta o link wa.me com a mensagem já preenchida (RF03)."""
    preco = f"{produto.preco:.2f}".replace(".", ",")
    mensagem = f"Olá! Tenho interesse no produto {produto.nome} (R$ {preco})."
    return f"https://wa.me/{settings.LOJA_WHATSAPP}?text={quote(mensagem)}"


def catalogo(request):
    """Catálogo público: produtos ativos, filtro por categoria e busca por nome (RF02, RF08)."""
    produtos = Produto.objects.ativos().select_related("categoria")
    categoria_atual = None
    slug = request.GET.get("categoria", "")
    if slug:
        categoria_atual = get_object_or_404(Categoria, slug=slug, ativa=True)
        produtos = produtos.filter(categoria=categoria_atual)
    busca = request.GET.get("q", "").strip()[:60]
    if busca:
        produtos = produtos.filter(Q(nome__icontains=busca))

    pagina = Paginator(produtos, ITENS_POR_PAGINA).get_page(request.GET.get("pagina"))
    for produto in pagina:
        produto.link_whatsapp = link_whatsapp(produto)

    return render(request, "loja/catalogo.html", {
        "pagina": pagina,
        "categorias": Categoria.objects.filter(ativa=True),
        "categoria_atual": categoria_atual,
        "busca": busca,
    })


class LoginComLimite(auth_views.LoginView):
    """Login com bloqueio temporário após tentativas repetidas (RNF01)."""

    template_name = "loja/login.html"

    def _chave(self):
        usuario = (self.request.POST.get("username") or "").lower()[:150]
        ip = self.request.META.get("REMOTE_ADDR", "")
        return f"login-falhas:{usuario}:{ip}"

    def post(self, request, *args, **kwargs):
        if cache.get(self._chave(), 0) >= settings.LOGIN_MAX_TENTATIVAS:
            form = self.get_form()
            form.add_error(None, "Muitas tentativas sem sucesso. Aguarde 15 minutos e tente novamente.")
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        chave = self._chave()
        cache.set(chave, cache.get(chave, 0) + 1, settings.LOGIN_JANELA_SEGUNDOS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._chave())
        return super().form_valid(form)


@login_required
def painel(request):
    pedidos_abertos = Pedido.objects.exclude(status__in=[Pedido.Status.ENTREGUE, Pedido.Status.CANCELADO])
    return render(request, "loja/painel.html", {
        "pedidos_abertos": pedidos_abertos.count(),
        "esgotados": Produto.objects.ativos().filter(esgotado=True).count(),
        "ultimos": Pedido.objects.select_related("registrado_por")[:5],
    })


@login_required
def produtos(request):
    return render(request, "loja/produtos.html", {
        "produtos": Produto.objects.select_related("categoria"),
    })


@login_required
def produto_form(request, pk=None):
    """Cadastro e edição de produto (RF01)."""
    produto = get_object_or_404(Produto, pk=pk) if pk else None
    form = ProdutoForm(request.POST or None, request.FILES or None, instance=produto)
    if request.method == "POST" and form.is_valid():
        salvo = form.save()
        situacao = "Esgotado" if salvo.esgotado else f"{salvo.quantidade_estoque} em estoque"
        messages.success(request, f"Produto {salvo.nome} salvo ({situacao}).")
        return redirect("loja:produtos")
    return render(request, "loja/produto_form.html", {"form": form, "produto": produto})


@login_required
def pedidos(request):
    """Lista de pedidos com filtro por status (RF06)."""
    status = request.GET.get("status", "")
    lista = Pedido.objects.prefetch_related("itens__produto")
    if status in Pedido.Status.values:
        lista = lista.filter(status=status)
    return render(request, "loja/pedidos.html", {
        "pedidos": lista,
        "status_atual": status,
        "status_opcoes": Pedido.Status.choices,
    })


@login_required
def novo_pedido(request):
    """Registro de pedido com baixa automática no estoque (RF04)."""
    form = NovoPedidoForm(request.POST or None)
    erro_estoque = None
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        try:
            pedido = services.registrar_pedido(
                usuario=request.user,
                cliente_nome=dados["cliente_nome"],
                cliente_telefone=dados["cliente_telefone"],
                endereco_entrega=dados["endereco_entrega"],
                forma_pagamento=dados["forma_pagamento"],
                itens=[services.ItemSolicitado(dados["produto"].pk, dados["quantidade"])],
            )
        except services.EstoqueInsuficiente as exc:
            erro_estoque = exc
            form.add_error("quantidade", f"Quantidade maior que o estoque: informe até {exc.disponivel}.")
        else:
            request.session["estoque_antes"] = {str(dados["produto"].pk): dados["produto"].quantidade_estoque}
            return redirect("loja:pedido_detalhe", pk=pedido.pk)
    contexto = {"form": form, "erro_estoque": erro_estoque}
    return render(request, "loja/novo_pedido.html", contexto, status=422 if erro_estoque else 200)


@login_required
def pedido_detalhe(request, pk):
    pedido = get_object_or_404(Pedido.objects.prefetch_related("itens__produto"), pk=pk)
    antes = request.session.pop("estoque_antes", {})
    itens = []
    for item in pedido.itens.all():
        itens.append({"item": item, "estoque_antes": antes.get(str(item.produto_id))})
    proximos = services.TRANSICOES.get(pedido.status, set())
    return render(request, "loja/pedido_detalhe.html", {
        "pedido": pedido,
        "itens": itens,
        "recem_criado": bool(antes),
        "proximos_status": [(s, Pedido.Status(s).label) for s in Pedido.Status.values if s in proximos],
    })


@login_required
@require_POST
def pedido_status(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    form = StatusForm(request.POST)
    if form.is_valid():
        try:
            services.alterar_status(pedido, form.cleaned_data["status"])
            messages.success(request, f"Status do pedido nº {pedido.numero} atualizado.")
        except services.TransicaoInvalida as exc:
            messages.error(request, str(exc))
    return redirect("loja:pedido_detalhe", pk=pk)


@login_required
def relatorio(request):
    hoje = timezone.localdate()
    try:
        ano = int(request.GET.get("ano", hoje.year))
        mes = int(request.GET.get("mes", hoje.month))
        if not 1 <= mes <= 12:
            raise ValueError
    except ValueError:
        ano, mes = hoje.year, hoje.month
    dados = services.relatorio_mensal(ano, mes)
    return render(request, "loja/relatorio.html", {"dados": dados, "ano": ano, "mes": mes})


def service_worker(request):
    """Serve o service worker na raiz, para que ele controle todas as páginas (PWA)."""
    caminho = finders.find("loja/sw.js")
    with open(caminho, encoding="utf-8") as arquivo:
        return HttpResponse(arquivo.read(), content_type="application/javascript")


def erro_404(request, exception):
    return render(request, "loja/erro.html", {"titulo": "Página não encontrada"}, status=404)


def erro_500(request):
    return render(request, "loja/erro.html", {"titulo": "Algo deu errado"}, status=500)
