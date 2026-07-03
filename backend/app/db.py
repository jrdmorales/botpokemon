import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def ensure_schema() -> None:
    """Bootstrap idempotente de tablas, tolerante a carreras entre servicios.

    api y scraper-worker arrancan a la vez y ambos llaman create_all; en
    PostgreSQL eso puede chocar con "duplicate key pg_type". Si otro proceso
    ganó la carrera, las tablas ya existen: reintentar y seguir.
    """
    import app.models  # noqa: F401 — registra tablas en Base.metadata

    for attempt in range(3):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except (IntegrityError, ProgrammingError, DBAPIError):
            if attempt == 2:
                raise
            await asyncio.sleep(2 * (attempt + 1))
