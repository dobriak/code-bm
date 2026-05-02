
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from raidio.db.settings import get_settings


def get_engine_uri() -> str:
    settings = get_settings()
    return settings.database_url


session_factory = sessionmaker(bind=create_engine(get_engine_uri()), expire_on_commit=False)


def get_db_session() -> Session:
    return session_factory()
