"""Configuración validada, sin credenciales implícitas."""

from functools import lru_cache

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_postgresql(cls, value: str) -> str:
        try:
            url = make_url(value)
        except (ArgumentError, TypeError, ValueError) as error:
            raise ValueError("DATABASE_URL is not a valid SQLAlchemy URL") from error
        if url.get_backend_name() != "postgresql" or not url.database:
            raise ValueError("DATABASE_URL must identify a PostgreSQL database")
        return value


@lru_cache
def get_settings() -> Settings:
    """Falla con un error de configuración si DATABASE_URL no existe."""
    try:
        return Settings()
    except ValidationError as error:
        raise RuntimeError(
            "DATABASE_URL is required and must be a valid SQLAlchemy URL"
        ) from error


def validate_test_database_url(
    test_database_url: str,
    development_database_url: str | None = None,
) -> str:
    """Impide que los tests apunten a desarrollo o a una base no aislada."""
    try:
        test_url = make_url(test_database_url)
        development_url = (
            make_url(development_database_url)
            if development_database_url is not None
            else None
        )
    except (ArgumentError, TypeError, ValueError) as error:
        raise RuntimeError("TEST_DATABASE_URL is not a valid SQLAlchemy URL") from error
    if test_url.get_backend_name() != "postgresql":
        raise RuntimeError("TEST_DATABASE_URL must use PostgreSQL")
    if test_url.database is None or not test_url.database.endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL database name must end with '_test'")
    if development_url is not None and test_url == development_url:
        raise RuntimeError("TEST_DATABASE_URL cannot equal DATABASE_URL")
    return test_database_url
