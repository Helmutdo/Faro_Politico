"""Fixtures compartidos, con aislamiento estricto de PostgreSQL."""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text

from trama_publica.core.config import validate_test_database_url


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    validated_url = validate_test_database_url(test_url, os.environ.get("DATABASE_URL"))
    engine = create_engine(validated_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("PostgreSQL integration tests require PostgreSQL")
    with engine.connect() as connection:
        if connection.scalar(text("SELECT current_database()")) != "faro_politico_test":
            raise RuntimeError("refusing to run outside faro_politico_test")
    yield engine
    engine.dispose()


@pytest.fixture
def clean_postgres(postgres_engine: Engine) -> Iterator[Engine]:
    yield postgres_engine
    with postgres_engine.begin() as connection:
        tables = connection.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public' AND tablename <> 'alembic_version'
                """
            )
        ).scalars()
        quoted = ", ".join(f'"{name}"' for name in tables)
        if quoted:
            connection.execute(text(f"TRUNCATE TABLE {quoted} CASCADE"))
