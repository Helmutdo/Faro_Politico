"""Protecciones de configuración de base de datos."""

import pytest
from pydantic import ValidationError

from trama_publica.core.config import Settings, validate_test_database_url


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "url",
    ["not-a-url", "sqlite:///faro.db", "postgresql+psycopg://localhost"],
)
def test_database_url_must_be_valid_postgresql(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=url, _env_file=None)


def test_test_url_cannot_target_development() -> None:
    development = "postgresql+psycopg://app@127.0.0.1:55432/faro_politico_dev"
    with pytest.raises(RuntimeError):
        validate_test_database_url(development, development)


def test_test_url_requires_test_database_suffix() -> None:
    with pytest.raises(RuntimeError):
        validate_test_database_url(
            "postgresql+psycopg://app@127.0.0.1:55432/faro_politico_dev"
        )
