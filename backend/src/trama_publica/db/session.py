"""Motor y factoría de sesiones SQLAlchemy."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from trama_publica.core.config import get_settings


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or get_settings().database_url
    return create_engine(resolved_url, pool_pre_ping=True)


def create_session_factory(
    database_url: str | None = None,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=create_database_engine(database_url),
        class_=Session,
        expire_on_commit=False,
    )
