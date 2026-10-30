from fastapi import FastAPI

from app.routers import categories, products

# O schema do banco é criado e evoluído pelo Alembic: `alembic upgrade head`.
app = FastAPI(
    title="API de Gerenciamento de Dados",
    description="API REST para cadastro e consulta de categorias e produtos, "
    "com persistência em banco relacional SQL.",
    version="1.0.0",
)

app.include_router(categories.router)
app.include_router(products.router)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}
