"""Fixtures de teste.

O banco é escolhido por `TEST_DATABASE_URL`:

- não definida  -> SQLite em memória (padrão, sem dependências);
- PostgreSQL    -> ex.: postgresql+psycopg://app:app@localhost:5432/data_management_test

Por segurança, bancos que não sejam SQLite devem terminar em `_test`, pois os
dados das tabelas são apagados entre os testes. Se o banco de teste não existir,
ele é criado automaticamente.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")
IS_SQLITE = make_url(TEST_DATABASE_URL).get_backend_name() == "sqlite"


def _admin_url(url: URL) -> URL:
    """URL do banco de manutenção `postgres`, usada para criar/remover bancos."""
    return url.set(database="postgres")


def _ensure_safe_database(url: URL) -> None:
    if not (url.database or "").endswith("_test"):
        pytest.exit(
            f"TEST_DATABASE_URL aponta para '{url.database}'. Por segurança, o banco de "
            "teste deve terminar em '_test' (os dados são apagados entre os testes).",
            returncode=2,
        )


def _create_database_if_missing(url: URL) -> None:
    admin = create_engine(
        _admin_url(url), isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5}
    )
    try:
        with admin.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def engine():
    url = make_url(TEST_DATABASE_URL)
    if IS_SQLITE:
        test_engine = create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    else:
        _ensure_safe_database(url)
        try:
            _create_database_if_missing(url)
        except OperationalError as exc:
            pytest.exit(
                f"Não foi possível conectar ao PostgreSQL ({exc.orig}). "
                "Suba o banco com `docker compose up -d db`.",
                returncode=2,
            )
        test_engine = create_engine(url, connect_args={"connect_timeout": 5})

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    """Esvazia as tabelas após cada teste (isolamento) e reinicia os IDs."""
    yield
    with engine.begin() as conn:
        if IS_SQLITE:
            # Sem AUTOINCREMENT, o SQLite reinicia os IDs ao esvaziar a tabela.
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
        else:
            names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory):
    """Sessão direta no banco, para testes que não passam pela API."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    """Cliente de teste da API usando o banco de teste configurado."""

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
