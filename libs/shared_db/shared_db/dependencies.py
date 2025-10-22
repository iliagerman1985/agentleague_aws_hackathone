"""Database dependencies for FastAPI."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared_db.db import AsyncSessionLocal


async def get_async_db() -> AsyncGenerator[AsyncSession]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
