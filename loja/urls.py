from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "loja"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("painel/entrar/", views.LoginComLimite.as_view(), name="login"),
    path("painel/sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("painel/", views.painel, name="painel"),
    path("painel/produtos/", views.produtos, name="produtos"),
    path("painel/produtos/novo/", views.produto_form, name="produto_novo"),
    path("painel/produtos/<int:pk>/editar/", views.produto_form, name="produto_editar"),
    path("painel/pedidos/", views.pedidos, name="pedidos"),
    path("painel/pedidos/novo/", views.novo_pedido, name="novo_pedido"),
    path("painel/pedidos/<int:pk>/", views.pedido_detalhe, name="pedido_detalhe"),
    path("painel/pedidos/<int:pk>/status/", views.pedido_status, name="pedido_status"),
    path("painel/relatorio/", views.relatorio, name="relatorio"),
]
