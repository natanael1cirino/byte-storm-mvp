from django.conf import settings


def loja(request):
    return {"LOJA_NOME": settings.LOJA_NOME}
