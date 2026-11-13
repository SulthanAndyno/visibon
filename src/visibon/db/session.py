"""Pengaturan sesi database SQLite asynchronous."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from visibon.config import get_settings
from visibon.db.models import Base

_engine = None
_sessionmaker = None


def get_db_path() -> Path:
    settings = get_settings()
    db_path = getattr(settings, "database_path", "visibon.db")
    return Path(db_path)


def get_engine():
    global _engine
    if _engine is None:
        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite+aiosqlite:///{db_path}"
        _engine = create_async_engine(db_url, echo=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def init_db() -> None:
    """Inisialisasi tabel di database jika belum ada."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper untuk mendapatkan sesi DB."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session
