# API de Gerenciamento de Dados

API REST em **Python** para cadastro, consulta, atualização e remoção de **categorias** e **produtos**, com persistência em banco relacional **SQL**.

Projeto pessoal para praticar o desenvolvimento de APIs com boas práticas de rotas, validação e modelagem de dados.

## Tecnologias

- **Python 3.12** + **FastAPI** (rotas, validação e documentação automática)
- **SQLAlchemy 2.0** (ORM) com **SQLite** (desenvolvimento/testes) ou **PostgreSQL** (via Docker) — troque apenas `DATABASE_URL`
- **Alembic** (migrations versionadas do schema)
- **Docker / docker-compose** (API + PostgreSQL)
- **Pydantic v2** (schemas de entrada/saída)
- **pytest** (testes de integração em SQLite e PostgreSQL)
- **Git/GitHub** para versionamento

## Estrutura

```
app/
├── main.py          # criação da aplicação e registro das rotas
├── config.py        # configurações via variáveis de ambiente
├── database.py      # engine, sessão e dependência get_db
├── models.py        # modelos ORM (tabelas, constraints, relacionamentos)
├── schemas.py       # schemas Pydantic (validação e serialização)
├── crud.py          # camada de acesso a dados
└── routers/         # endpoints agrupados por recurso
migrations/          # migrations do Alembic
tests/               # testes automatizados
Dockerfile · docker-compose.yml   # API + PostgreSQL
```

## Como executar

O banco é selecionado pela variável `DATABASE_URL`. O schema é gerenciado pelo **Alembic**, então rode as migrations antes de iniciar a API.

### Opção 1 — SQLite (sem instalar nada)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

alembic upgrade head
uvicorn app.main:app --reload
```

O arquivo `data.db` é criado na raiz do projeto.

### Opção 2 — PostgreSQL com Docker

```bash
docker compose up --build
```

Sobe o PostgreSQL 16 e a API (as migrations são aplicadas automaticamente na inicialização). Para rodar a API localmente contra o Postgres do compose:

```bash
docker compose up -d db
# Defina DATABASE_URL (veja .env.example), por exemplo:
# postgresql+psycopg://app:app@localhost:5432/data_management
alembic upgrade head
uvicorn app.main:app --reload
```

Documentação interativa (Swagger): http://127.0.0.1:8000/docs

### Migrations

```bash
alembic upgrade head                                   # aplica as migrations
alembic revision --autogenerate -m "descrição"         # gera migration após alterar models.py
alembic downgrade -1                                   # desfaz a última migration
```

Um teste automatizado garante que os modelos e as migrations não fiquem dessincronizados.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/categories` | Cria categoria |
| GET | `/categories` | Lista categorias (paginado) |
| GET | `/categories/{id}` | Detalha categoria |
| PATCH | `/categories/{id}` | Atualiza parcialmente |
| DELETE | `/categories/{id}` | Remove (bloqueado se houver produtos) |
| POST | `/products` | Cria produto |
| GET | `/products` | Lista produtos com filtros e paginação |
| GET | `/products/{id}` | Detalha produto |
| PATCH | `/products/{id}` | Atualiza parcialmente |
| DELETE | `/products/{id}` | Remove produto |
| GET | `/health` | Verificação de saúde |

Filtros de `GET /products`: `search` (nome), `category_id`, `min_price`, `max_price`, `limit` (1–100) e `offset`.

### Exemplo

```bash
curl -X POST http://127.0.0.1:8000/categories -H "Content-Type: application/json" \
     -d '{"name": "Eletrônicos"}'

curl -X POST http://127.0.0.1:8000/products -H "Content-Type: application/json" \
     -d '{"name": "Teclado mecânico", "price": "249.90", "stock": 10, "category_id": 1}'

curl "http://127.0.0.1:8000/products?search=teclado&max_price=300"
```

## Boas práticas aplicadas

- Rotas RESTful no plural, com verbos HTTP e códigos de status adequados (`201`, `204`, `404`, `409`, `422`)
- Separação em camadas: rotas → acesso a dados → modelos
- Validação de entrada com Pydantic (preço e estoque não negativos, tamanhos máximos)
- Integridade no banco: chave estrangeira, `UNIQUE` e `CHECK` constraints
- Valores monetários com `Decimal`/`NUMERIC` (sem `float`)
- Paginação e filtros nas listagens
- Configuração por variáveis de ambiente

## Testes

Por padrão, os testes rodam em **SQLite em memória** (sem dependências):

```bash
pytest
```

Para rodar a mesma suíte contra **PostgreSQL**, suba o banco e defina `TEST_DATABASE_URL`:

```bash
docker compose up -d db

# Windows (PowerShell)
$env:TEST_DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/data_management_test"
# Linux/macOS
export TEST_DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/data_management_test"

pytest
```

- O banco `data_management_test` é criado automaticamente se não existir, separado do banco de desenvolvimento.
- Por segurança, bancos que não sejam SQLite **precisam terminar em `_test`**, pois as tabelas são esvaziadas entre os testes.
- A suíte cobre as rotas, as constraints aplicadas pelo próprio banco (`CHECK`, chave estrangeira, `UNIQUE`) e as migrations (upgrade, downgrade e ausência de divergência com os modelos).

## Próximos passos

- Autenticação (JWT)
- CI com GitHub Actions (rodar a suíte em SQLite e PostgreSQL)
