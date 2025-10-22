import asyncio
import sys

from sqlalchemy.exc import SQLAlchemyError

from common.core.config_service import ConfigService
from common.utils.utils import get_logger
from shared_db.db import Base, engine
from shared_db.db.create_database import create_database
from shared_db.db.run_migrations import run_migrations

# Get logger for this module
logger = get_logger()


async def init_db() -> bool | None:
    """Initialize the database by:
    1. Creating the database if it doesn't exist (PostgreSQL only)
    2. Running migrations to ensure schema is up to date
    3. Falling back to create_all() if migrations fail or for SQLite
    """
    try:
        # Get database URL to determine database type
        config_service = ConfigService()
        db_url = config_service.get_database_url()

        if db_url.startswith("sqlite"):
            # For SQLite (testing), use create_all directly with async engine
            logger.info(
                "Using SQLite - creating tables with create_all()",
                operation="create_sqlite_tables",
            )
            # Use run_sync to execute synchronous create_all on async engine
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(
                "SQLite database tables created successfully",
                operation="create_sqlite_tables",
                status="success",
            )
            return True
        else:
            # For PostgreSQL, follow the original process
            # Step 1: Create database if it doesn't exist
            logger.info(
                "Creating database if it doesn't exist",
                operation="create_database",
            )
            db_created = create_database()
            if not db_created:
                logger.error(
                    "Failed to create database",
                    operation="create_database",
                    status="error",
                )
                return False

            # Step 2: Run migrations to ensure schema is up to date
            logger.info("Running database migrations", operation="run_migrations")
            migrations_success = run_migrations()

            if migrations_success:
                logger.info(
                    "Database migrations completed successfully",
                    operation="run_migrations",
                    status="success",
                )
                return True
            else:
                logger.warning(
                    "Migrations failed, falling back to create_all()",
                    operation="run_migrations",
                    status="warning",
                )

                # Step 3: Fallback to async create_all() if migrations fail
                logger.info(
                    "Creating database tables using SQLAlchemy create_all()",
                    operation="create_tables_fallback",
                )
                # Use run_sync to execute synchronous create_all on async engine
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info(
                    "Database tables created successfully using fallback method",
                    operation="create_tables_fallback",
                    status="success",
                )
                return True

    except SQLAlchemyError as e:
        logger.exception(
            "Error during database initialization",
            operation="init_db",
            status="error",
            error=str(e),
        )
        return False
    except Exception as e:
        logger.exception(
            "Unexpected error during database initialization",
            operation="init_db",
            status="error",
            error=str(e),
        )
        return False


if __name__ == "__main__":
    # This allows the script to be run directly
    import asyncio

    if not db_url.startswith("sqlite"):
        # First, create the database if it doesn't exist (PostgreSQL only)
        logger.info("Ensuring database exists...")
        if not create_database():
            logger.error("Failed to create database")
            sys.exit(1)

    # Then initialize the database schema
    success = asyncio.run(init_db())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # This allows the script to be run directly
    asyncio.run(main())
