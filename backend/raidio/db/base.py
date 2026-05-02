from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from raidio.db.settings import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


def get_session_factory():
    engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
