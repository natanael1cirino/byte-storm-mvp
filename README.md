# Byte Storm: catálogo online com controle de estoque e pedidos

MVP desenvolvido na disciplina **Projeto de Software** (Experiências Práticas 1 a 3) para a **Byte Storm**,
loja de eletrônicos e acessórios de Três Corações (MG) que vende pelo Instagram e pelo WhatsApp.

O sistema liga **catálogo, estoque e pedidos**: o cliente consulta preço e disponibilidade sozinho e fecha a
compra pelo WhatsApp; o sócio registra o pedido no painel e o estoque baixa automaticamente, marcando o
produto como esgotado quando chega a zero.

> Todos os dados de demonstração deste repositório são **fictícios**.

**Em produção:** https://natanaelcirino.pythonanywhere.com/ (catálogo público; painel em `/painel/`).
A disponibilidade é verificada a cada 30 minutos pelo workflow
[Monitoramento de disponibilidade](.github/workflows/monitoramento.yml).

## Funcionalidades

| Requisito | O que faz |
|---|---|
| RF01 | Cadastro e edição de produtos (nome, categoria, preço, estoque, foto convertida para WebP) |
| RF02 | Catálogo público por link, com filtro por categoria e selo Disponível/Esgotado |
| RF03 | Botão **Comprar pelo WhatsApp** com nome e preço já preenchidos |
| RF04 | Registro de pedido com baixa automática no estoque, em transação, bloqueando estoque insuficiente |
| RF05 | Produto marcado como esgotado automaticamente quando o estoque zera |
| RF06 | Mudança de status (novo → pago → em entrega → entregue) e cancelamento que devolve o estoque |
| RF07 | Relatório mensal com faturamento e produtos mais vendidos |
| RF08 | Busca por nome no catálogo |

Segurança (RNF01/RNF02): login obrigatório no painel, senhas com hash PBKDF2, bloqueio após 5 tentativas,
CSRF, escape automático de HTML, Content-Security-Policy e consultas apenas pelo ORM.
Acessibilidade (RNF04): alvos de toque de 48 px, rótulos visíveis, estados com texto e ícone além da cor.

## Tecnologias

Python 3.12 · Django 5.2 LTS (padrão MVT) · MySQL 8 em produção e no CI (SQLite no desenvolvimento local) ·
Pillow · pytest-django · GitHub Actions · PWA (manifest + service worker).

## Arquitetura

```
loja/
  models.py      Categoria, Produto, Pedido, ItemPedido
  services.py    regras de negócio: registrar_pedido, alterar_status, relatorio_mensal
  forms.py       validação no servidor
  views.py       catálogo público e painel (só validam e chamam os serviços)
  templates/     telas mobile-first
tests/           testes de serviços, telas e segurança
```

## Como rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createcachetable
set DEMO_SENHA=uma-senha-de-teste  # Linux/macOS: export DEMO_SENHA=...
python manage.py carregar_demo     # produtos fictícios + usuário socio.teste
python manage.py runserver
```

Catálogo: http://127.0.0.1:8000/ · Painel: http://127.0.0.1:8000/painel/

## Testes e qualidade

```bash
pytest --cov=loja
ruff check .
```

O workflow `.github/workflows/ci.yml` roda lint, verificação de migrações, testes com MySQL 8 e
`pip-audit` a cada push e pull request na branch `main`.

## Implantação

Configuração por variáveis de ambiente (ver `.env.exemplo`); nenhuma chave ou senha fica no código.

Publicado no **PythonAnywhere** (plano gratuito, Python 3.12):

1. `git clone` do repositório e virtualenv com `pip install -r requirements.txt`.
2. Arquivo `~/.bytestorm.env` (fora do repositório, permissão 600) com `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`,
   `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` e `DJANGO_ATRAS_DE_PROXY_HTTPS=true`.
3. `python manage.py migrate`, `createcachetable` e `collectstatic`.
4. WSGI do PythonAnywhere carregando o `.bytestorm.env` e `bytestorm.wsgi`; arquivos estáticos mapeados em
   `/static/` → `staticfiles/`; HTTPS forçado.

No plano gratuito o banco de produção é SQLite em disco persistente (um único processo web). O MySQL 8
continua sendo usado no pipeline de CI e pode ser ativado em produção com `DB_ENGINE=mysql`.

## Autor

Natanael Cirino — Ciência da Computação.
