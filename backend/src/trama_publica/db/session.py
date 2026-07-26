"""Motor y factoría de sesiones SQLAlchemy."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from trama_publica.core.config import settings


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or settings.database_url, pool_pre_ping=True)


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
