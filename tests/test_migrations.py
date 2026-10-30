import uuid

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.database import Base
from tests.conftest import IS_SQLITE, TEST_DATABASE_URL


@pytest.fixture()
def migration_url(tmp_path):
    """URL de um banco vazio e descartável, no mesmo SGBD dos demais testes."""
    if IS_SQLITE:
        yield f"sqlite:///{tmp_path / 'migration.db'}"
        return

    base_url = make_url(TEST_DATABASE_URL)
    name = f"migration_{uuid.uuid4().hex[:8]}_test"
    admin = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield base_url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _alembic_config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


def _table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migrations_upgrade_and_downgrade(migration_url):
    config = _alembic_config(migration_url)

    command.upgrade(config, "head")
    assert {"categories", "products"} <= _table_names(migration_url)

    command.downgrade(config, "base")
    assert not {"categories", "products"} & _table_names(migration_url)


def test_migrations_match_models(migration_url):
    """Falha se os modelos mudarem sem uma migration correspondente."""
    command.upgrade(_alembic_config(migration_url), "head")

    engine = create_engine(migration_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()
