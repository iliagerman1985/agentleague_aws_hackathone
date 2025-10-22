#!/usr/bin/env python3
"""Database reset utility that properly drops all tables including handling foreign key constraints."""

import asyncio
import sys

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from common.utils.utils import get_logger
from shared_db.db import engine

# Get logger for this module
logger = get_logger(__name__)


async def clear_database_data() -> bool:
    """Clear all data from database tables without dropping the tables themselves.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with engine.begin() as conn:
            # Get all table names from the database using run_sync for inspection
            def get_table_info(sync_conn: Connection) -> list[str]:
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                return tables

            tables = await conn.run_sync(get_table_info)
            logger.info(f"Found tables to clear: {tables}")

            if tables:
                # Disable foreign key constraints temporarily for safe deletion
                logger.info("Disabling foreign key constraints")
                await conn.execute(text("SET session_replication_role = replica"))

                # Clear all tables (delete data but keep table structure)
                for table in tables:
                    if table != "alembic_version":  # Don't clear alembic version table
                        # Validate table name to prevent SQL injection
                        if table.replace("_", "").replace("-", "").isalnum():
                            logger.info(f"Clearing data from table: {table}")
                            # Use string literal for table name - safe after validation
                            await conn.execute(text(f'DELETE FROM "{table}"'))  # noqa: S608
                        else:
                            logger.warning(f"Skipping invalid table name: {table}")

                # Re-enable foreign key constraints
                logger.info("Re-enabling foreign key constraints")
                await conn.execute(text("SET session_replication_role = DEFAULT"))

                logger.info("All table data cleared successfully")
            else:
                logger.info("No tables found to clear")

        # Verify data is cleared but tables exist
        async with engine.begin() as conn:

            def verify_tables(sync_conn: Connection) -> list[str]:
                inspector = inspect(sync_conn)
                return inspector.get_table_names()

            remaining_tables = await conn.run_sync(verify_tables)
            if remaining_tables:
                logger.info(f"Verified: Tables structure preserved: {remaining_tables}")
                return True
            else:
                logger.error("Warning: No tables found after clearing data")
                return False

    except Exception:
        logger.exception("Error clearing table data")
        return False


async def reset_database() -> bool:
    """Reset the database by dropping all tables.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with engine.begin() as conn:
            # Get all table names from the database using run_sync for inspection
            def get_table_info(sync_conn: Connection) -> list[str]:
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                return tables

            tables = await conn.run_sync(get_table_info)
            logger.info(f"Found tables to drop: {tables}")

            if tables:
                # Disable foreign key checks temporarily (PostgreSQL)
                logger.info("Disabling foreign key constraints")
                await conn.execute(text("SET session_replication_role = replica"))

                # Drop all tables
                for table in tables:
                    # Validate table name to prevent SQL injection
                    if table.replace("_", "").replace("-", "").isalnum():
                        logger.info(f"Dropping table: {table}")
                        # Use string literal for table name - safe after validation
                        await conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    else:
                        logger.warning(f"Skipping invalid table name: {table}")

                # Drop alembic_version table specifically
                logger.info("Dropping alembic_version table")
                await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

                # Re-enable foreign key checks
                logger.info("Re-enabling foreign key constraints")
                await conn.execute(text("SET session_replication_role = DEFAULT"))

                logger.info("All tables dropped successfully")
            else:
                logger.info("No tables found to drop")

            # Drop custom enum types (PostgreSQL specific)
            logger.info("Dropping custom enum types")
            result = await conn.execute(
                text("""
                SELECT typname FROM pg_type
                WHERE typtype = 'e'
                AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            """)
            )
            enum_types = [row[0] for row in result]
            logger.info(f"Found enum types to drop: {enum_types}")

            for enum_type in enum_types:
                # Validate enum type name to prevent SQL injection
                if enum_type.replace("_", "").replace("-", "").isalnum():
                    logger.info(f"Dropping enum type: {enum_type}")
                    # Use string literal for enum type name - safe after validation
                    await conn.execute(text(f'DROP TYPE IF EXISTS "{enum_type}" CASCADE'))
                else:
                    logger.warning(f"Skipping invalid enum type name: {enum_type}")

            logger.info("All enum types dropped successfully")

        # Verify tables are gone
        async with engine.begin() as conn:

            def verify_tables(sync_conn: Connection) -> list[str]:
                inspector = inspect(sync_conn)
                return inspector.get_table_names()

            remaining_tables = await conn.run_sync(verify_tables)
            if remaining_tables:
                logger.error(f"Warning: Some tables still exist: {remaining_tables}")
                return False
            else:
                logger.info("Verified: All tables successfully removed")
                return True

    except Exception:
        logger.exception("Error dropping tables")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database reset and clear utilities")
    parser.add_argument("--clear-data", action="store_true", help="Clear all table data without dropping tables")
    parser.add_argument("--drop-tables", action="store_true", help="Drop all tables (default behavior)")

    args = parser.parse_args()

    if args.clear_data:
        success = asyncio.run(clear_database_data())
        if success:
            print("✓ Database data cleared successfully")  # noqa: T201
            sys.exit(0)
        else:
            print("❌ Database data clear failed")  # noqa: T201
            sys.exit(1)
    else:  # Default to dropping tables
        success = asyncio.run(reset_database())
        if success:
            print("✓ Database reset successful")  # noqa: T201
            sys.exit(0)
        else:
            print("❌ Database reset failed")  # noqa: T201
            sys.exit(1)
