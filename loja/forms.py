"""Formulários com validação no servidor (RNF02)."""
from io import BytesIO
from pathlib import Path

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, UnidentifiedImageError

from .models import Pedido, Produto

FOTO_LARGURA_MAX = 800


def converter_para_webp(arquivo):
    """Reprocessa a foto enviada: valida que é imagem, limita a largura e salva em WebP."""
    try:
        imagem = Image.open(arquivo)
        imagem.verify()
        arquivo.seek(0)
        imagem = Image.open(arquivo).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise forms.ValidationError("Envie uma imagem válida (JPG, PNG ou WebP).") from exc

    if imagem.width > FOTO_LARGURA_MAX:
        altura = round(imagem.height * FOTO_LARGURA_MAX / imagem.width)
        imagem = imagem.resize((FOTO_LARGURA_MAX, altura))

    buffer = BytesIO()
    imagem.save(buffer, format="WEBP", quality=80)
    nome = Path(arquivo.name).stem[:60] + ".webp"
    return InMemoryUploadedFile(buffer, "foto", nome, "image/webp", buffer.tell(), None)


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "categoria", "preco", "quantidade_estoque", "descricao", "foto", "ativo"]
        labels = {
            "nome": "Nome do produto",
            "preco": "Preço (R$)",
            "quantidade_estoque": "Quantidade em estoque",
            "descricao": "Descrição",
            "ativo": "Exibir no catálogo",
        }
        widgets = {
            "preco": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "inputmode": "decimal"}),
            "quantidade_estoque": forms.NumberInput(attrs={"min": "0", "inputmode": "numeric"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_preco(self):
        preco = self.cleaned_data["preco"]
        if preco is None or preco <= 0:
            raise forms.ValidationError("O preço deve ser maior que zero.")
        return preco

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto and hasattr(foto, "content_type"):
            return converter_para_webp(foto)
        return foto


class ProdutoComEstoqueField(forms.ModelChoiceField):
    """Mostra o saldo ao lado do nome, para o sócio ver o estoque antes de salvar."""

    def label_from_instance(self, obj):
        return f"{obj.nome} — {obj.quantidade_estoque} em estoque"


class NovoPedidoForm(forms.Form):
    produto = ProdutoComEstoqueField(
        queryset=Produto.objects.ativos().filter(esgotado=False),
        label="Produto",
        empty_label="Selecione o produto",
    )
    quantidade = forms.IntegerField(
        label="Quantidade", min_value=1, initial=1,
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "min": "1"}),
    )
    cliente_nome = forms.CharField(label="Nome do cliente", max_length=100)
    cliente_telefone = forms.RegexField(
        label="Telefone (WhatsApp)", max_length=20, regex=r"^[0-9()+\-\s]{8,20}$",
        error_messages={"invalid": "Informe um telefone com DDD, usando apenas números, espaços, parênteses ou hífen."},
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "off"}),
    )
    endereco_entrega = forms.CharField(
        label="Endereço de entrega", max_length=255, required=False,
        help_text="Opcional: deixe vazio quando o cliente for retirar.",
    )
    forma_pagamento = forms.ChoiceField(
        label="Forma de pagamento", choices=Pedido.FormaPagamento.choices, widget=forms.RadioSelect,
        initial=Pedido.FormaPagamento.PIX,
    )


class StatusForm(forms.Form):
    status = forms.ChoiceField(choices=Pedido.Status.choices)
