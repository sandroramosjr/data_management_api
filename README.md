# API de Gerenciamento de Dados

[![CI](https://github.com/sandroramosjr/data_management_api/actions/workflows/ci.yml/badge.svg)](https://github.com/sandroramosjr/data_management_api/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL 16](https://img.shields.io/badge/postgresql-16-4169E1?logo=postgresql&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

API REST construída em **Python** para manipulação, consulta e persistência de **categorias** e **produtos** em banco de dados relacional **SQL**, aplicando boas práticas de design de rotas HTTP, validação, estruturas de dados tipadas e evolução controlada de schema.

## Tecnologias

- **Python 3.12** + **FastAPI** — rotas RESTful, injeção de dependências e documentação OpenAPI automática
- **SQLAlchemy 2.0** — mapeamento relacional tipado (`Mapped[...]`), consultas parametrizadas, `JOIN`s e agregações SQL
- **PostgreSQL 16** (produção/Docker) e **SQLite** (desenvolvimento rápido/testes locais), selecionados apenas via `DATABASE_URL`
- **Alembic** — migrations versionadas do banco de dados (com suporte a batch mode no SQLite e `TIMESTAMPTZ` no PostgreSQL)
- **Pydantic v2** — validação estrita de entrada, serialização e schemas genéricos
- **pytest** + **Ruff** + **GitHub Actions** — suíte automatizada (>95% de cobertura) validada em SQLite e PostgreSQL a cada push

## Modelagem Relacional (SQL)

```mermaid
erDiagram
    CATEGORIES ||--o{ PRODUCTS : "possui (ON DELETE RESTRICT)"
    CATEGORIES {
        int id PK
        varchar_100 name UK "NOT NULL, UNIQUE INDEX"
        varchar_255 description "NULL"
    }
    PRODUCTS {
        int id PK
        varchar_150 name "NOT NULL, INDEX"
        varchar_500 description "NULL"
        numeric_10_2 price "NOT NULL, CHECK (price >= 0)"
        int stock "NOT NULL, CHECK (stock >= 0)"
        int category_id FK "NOT NULL, INDEX"
        timestamptz created_at "NOT NULL"
        timestamptz updated_at "NOT NULL"
    }
```

Além dos índices individuais em `categories.name`, `products.name` e `products.category_id`, a tabela `products` possui o índice composto `ix_products_category_price (category_id, price)` para acelerar consultas filtradas por categoria e faixa/ordenação de preço.

## Decisões Técnicas e Boas Práticas

### SQL e Persistência Relacional
- **Integridade garantida no SGBD:** chaves estrangeiras com `ON DELETE RESTRICT` (habilitadas explicitamente via `PRAGMA foreign_keys=ON` também no SQLite), índice `UNIQUE` em nomes de categorias e `CHECK` constraints impedindo preços ou estoques negativos mesmo fora da API.
- **Precisão monetária:** valores financeiros trafegam como `Decimal` em Python e são persistidos como `NUMERIC(10, 2)` no banco, evitando erros de ponto flutuante binário (`float`).
- **Prevenção de N+1 queries:** listagens e leituras de produtos carregam a categoria associada em uma única consulta com `JOIN` (`joinedload`), validado por teste automatizado que conta os `SELECT`s emitidos.
- **Agregação relacional em SQL:** `GET /categories/summary` calcula total de produtos, estoque acumulado, valor total do inventário e ticket médio por categoria diretamente no banco via `LEFT OUTER JOIN`, `GROUP BY`, `COUNT(products.id)` e `COALESCE`, preservando categorias sem produtos cadastrados.
- **Consultas seguras e determinísticas:** checagem de existência com `SELECT EXISTS(...)`, busca textual parcial com escape automático de curingas SQL (`%` e `_`) e ordenação composta com chave primária como critério de desempate para paginação estável.

### Python, Rotas e Estruturas de Dados
- **Separação em camadas:** rotas HTTP (`app/routers/`), contratos e estruturas de dados (`app/schemas.py`), camada de acesso a dados (`app/crud.py`) e modelos relacionais (`app/models.py`).
- **Estruturas de dados tipadas (Python 3.12):** objetos de valor imutáveis e enxutos em memória com `@dataclass(frozen=True, slots=True)` (`PaginationParams`, `ProductFilter`), enumerações `StrEnum` para parâmetros de ordenação, tabela de despacho `dict` para colunas SQL, `frozenset` para validação de campos obrigatórios em `PATCH` e paginação genérica `Page[T]` (PEP 695) com indicador `has_more`.
- **Semântica HTTP e validação estrita:** recursos no plural, códigos de status adequados (`200`, `201` com cabeçalho `Location`, `204`, `404`, `409`, `422`, `503`), rejeição de campos desconhecidos (`extra="forbid"`), remoção de espaços laterais e bloqueio de `null` em colunas não anuláveis durante atualizações parciais (`PATCH`).

## Estrutura do Repositório

```text
app/
├── main.py          # instância FastAPI, metadados OpenAPI e rota /health
├── config.py        # leitura tipada de variáveis de ambiente (.env)
├── database.py      # engine SQLAlchemy, sessão por requisição e PRAGMA SQLite
├── models.py        # modelos ORM, constraints, relacionamentos e índices
├── schemas.py       # schemas Pydantic v2, StrEnums e dataclasses de filtro
├── crud.py          # consultas SQL, JOINs, agregações e transações
└── routers/         # rotas agrupadas por recurso (/categories e /products)
migrations/          # histórico incremental de migrations (Alembic)
tests/               # testes de API, constraints de banco, N+1 e migrations
Dockerfile           # imagem de produção com usuário não-root
docker-compose.yml   # orquestração da API com PostgreSQL 16
pyproject.toml       # metadados do projeto e configuração de pytest, coverage e Ruff
```

## Endpoints

| Método | Rota | Status | Descrição |
|--------|------|--------|-----------|
| `POST` | `/categories` | `201` | Cria categoria (retorna `Location: /categories/{id}`) |
| `GET` | `/categories` | `200` | Lista categorias paginadas (`limit`, `offset`, `has_more`) |
| `GET` | `/categories/summary` | `200` | Resumo agregado em SQL (produtos, estoque, valor total e preço médio) |
| `GET` | `/categories/{id}` | `200` | Detalha categoria pelo ID |
| `PATCH` | `/categories/{id}` | `200` | Atualiza parcialmente uma categoria |
| `DELETE` | `/categories/{id}` | `204` | Remove categoria (retorna `409` se houver produtos vinculados) |
| `POST` | `/products` | `201` | Cria produto vinculado a uma categoria existente |
| `GET` | `/products` | `200` | Lista produtos com filtros, ordenação e paginação |
| `GET` | `/products/{id}` | `200` | Detalha produto com sua categoria aninhada |
| `PATCH` | `/products/{id}` | `200` | Atualiza parcialmente um produto |
| `DELETE` | `/products/{id}` | `204` | Remove produto |
| `GET` | `/health` | `200` | Verifica saúde da API e conectividade com o banco (`SELECT 1`) |

**Parâmetros de consulta em `GET /products`:**
- Filtros: `search` (nome parcial), `category_id`, `min_price`, `max_price`, `in_stock` (`true`/`false`)
- Ordenação: `sort_by` (`id`, `name`, `price`, `stock`, `created_at`) e `sort_order` (`asc`, `desc`)
- Paginação: `limit` (`1`–`100`, padrão `20`) e `offset` (padrão `0`)

### Exemplos de Requisição

```bash
# Criar categoria
curl -i -X POST http://127.0.0.1:8000/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "Eletrônicos", "description": "Periféricos e hardware"}'

# Criar produto
curl -X POST http://127.0.0.1:8000/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Teclado mecânico", "price": "249.90", "stock": 10, "category_id": 1}'

# Consultar produtos disponíveis ordenados pelo menor preço
curl "http://127.0.0.1:8000/products?in_stock=true&max_price=300&sort_by=price&sort_order=asc"

# Consultar agregação de inventário por categoria
curl "http://127.0.0.1:8000/categories/summary"
```

## Como Executar

### Opção 1 — Localmente com SQLite (zero dependências externas)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

alembic upgrade head
uvicorn app.main:app --reload
```

### Opção 2 — PostgreSQL 16 com Docker Compose

```bash
docker compose up --build
```

O serviço `db` aguarda `pg_isready` antes de iniciar a API, que aplica `alembic upgrade head` automaticamente. Para rodar a API fora do container apontando para o PostgreSQL do Docker, copie `.env.example` para `.env`, descomente a `DATABASE_URL` do Postgres e suba apenas o banco com `docker compose up -d db`.

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

### Gerenciamento de Migrations (Alembic)

```bash
alembic upgrade head                                   # aplica todas as migrations pendentes
alembic revision --autogenerate -m "descrição"         # gera nova migration a partir de models.py
alembic downgrade -1                                   # reverte a última migration
```

## Qualidade de Código e Testes

Por padrão, a suíte roda em **SQLite em memória**:

```bash
ruff check .
ruff format --check .
pytest --cov=app
```

Para executar exatamente a mesma suíte contra **PostgreSQL 16**:

```bash
docker compose up -d db

# Windows (PowerShell)
$env:TEST_DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/data_management_test"
# Linux/macOS
export TEST_DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/data_management_test"

pytest --cov=app
```

- O banco `data_management_test` é criado automaticamente se não existir, isolado do banco de desenvolvimento.
- Por segurança, bancos não-SQLite exigem o sufixo `_test`, pois as tabelas sofrem `TRUNCATE ... RESTART IDENTITY` entre cada teste.
- A suíte valida contratos HTTP, constraints nativas do SGBD, ausência de queries N+1, ciclo completo de `upgrade`/`downgrade` do Alembic e sincronia entre `models.py` e as migrations.

## Licença

Distribuído sob a licença [MIT](LICENSE).
