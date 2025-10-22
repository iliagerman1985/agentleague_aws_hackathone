# Shared database configuration
import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase as _DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker
from sqlalchemy.sql import func

from common.core.config_service import ConfigService
from common.db.db_utils import DateTimeUTC

# Initialize config service
config_service = ConfigService()
DATABASE_URL = config_service.get_database_url()

# Convert database URL to async version
async_database_url = DATABASE_URL
if config_service.is_testing() and DATABASE_URL.startswith("sqlite"):
    # For testing with multiple workers, use in-memory SQLite with shared cache
    if os.getenv("PLAYWRIGHT_WORKERS", "1") != "1" or os.getenv("USE_MEMORY_DB", "false").lower() == "true":
        async_database_url = "sqlite+aiosqlite:///:memory:?cache=shared"
        # Enable WAL mode for better concurrency
        engine = create_async_engine(
            async_database_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
            },
            pool_pre_ping=True,
            echo=False,
        )
    else:
        # Use file-based SQLite for single worker testing
        if not DATABASE_URL.startswith("sqlite+aiosqlite"):
            async_database_url = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        engine = create_async_engine(async_database_url, connect_args={"check_same_thread": False}, pool_pre_ping=True, echo=False)
else:
    # Production/development database - convert to async if needed
    if DATABASE_URL.startswith("postgresql://"):
        async_database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    elif DATABASE_URL.startswith("postgres://"):
        # Handle postgres alias
        async_database_url = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")
    elif DATABASE_URL.startswith("sqlite://"):
        async_database_url = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

    # Configure connection pool for long-polling support
    # Increase pool size to handle multiple long-polling requests + background workers
    engine = create_async_engine(
        async_database_url,
        pool_size=20,  # Increased from default 5
        max_overflow=30,  # Increased from default 10
        pool_timeout=30,  # Wait up to 30 seconds for a connection
        pool_pre_ping=True,  # Verify connections before using them
    )

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


def get_sync_database_url() -> str:
    """Get synchronous database URL for testing."""
    sync_url = DATABASE_URL
    if config_service.is_testing() and DATABASE_URL.startswith("sqlite"):
        # Use the same file-based SQLite for sync operations
        sync_url = DATABASE_URL
    elif DATABASE_URL.startswith("postgresql+asyncpg://"):
        # Convert async PostgreSQL URL to sync
        sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    elif sync_url.startswith("sqlite+aiosqlite://"):
        # Convert async SQLite URL to sync
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
    return sync_url


# Create synchronous sessionmaker for mock JWT validator and other sync operations
sync_database_url = get_sync_database_url()
sync_engine = create_engine(sync_database_url, connect_args={"check_same_thread": False} if "sqlite" in sync_database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def create_sync_session():
    """Create synchronous database session for testing."""
    return SessionLocal()


class Base(_DeclarativeBase):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(DateTimeUTC(), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTimeUTC(),
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
