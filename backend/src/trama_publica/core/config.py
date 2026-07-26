"""Configuración validada de la aplicación."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://trama_publica:trama_publica_dev"
        "@localhost:5432/trama_publica"
    )


settings = Settings()
