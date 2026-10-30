from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import categories, products

# O schema do banco é criado e evoluído pelo Alembic: `alembic upgrade head`.
app = FastAPI(
    title="API de Gerenciamento de Dados",
    description=(
        "API REST para manipulação e persistência de categorias e produtos em banco "
        "relacional SQL, com validação, paginação, filtros, ordenação e agregações."
    ),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Categorias",
            "description": "Cadastro, consulta e resumo agregado de categorias.",
        },
        {
            "name": "Produtos",
            "description": "Cadastro, consulta filtrada/ordenada e manutenção de produtos.",
        },
        {
            "name": "Sistema",
            "description": "Diagnóstico de disponibilidade da aplicação e do banco.",
        },
    ],
)

app.include_router(categories.router)
app.include_router(products.router)


@app.get(
    "/health",
    tags=["Sistema"],
    summary="Verifica disponibilidade da API e conectividade SQL",
)
def health(db: Annotated[Session, Depends(get_db)]):
    try:
        db.execute(select(1))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Banco de dados indisponível.",
        ) from exc
    return {"status": "ok"}
