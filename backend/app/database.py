from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


def _sqlite_url(path_or_url: str) -> str:
    if path_or_url.startswith("sqlite"):
        return path_or_url
    return f"sqlite+aiosqlite:///{path_or_url}"


class Base(DeclarativeBase):
    pass


engine = create_async_engine(_sqlite_url(settings.database_url), echo=settings.debug)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session
