from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

database_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[None]:
    """Own a service transaction even when authentication already triggered autobegin."""
    if not session.in_transaction():
        async with session.begin():
            yield
        return

    try:
        yield
    except BaseException:
        await session.rollback()
        raise
    else:
        await session.commit()


async def dispose_engine() -> None:
    await engine.dispose()
