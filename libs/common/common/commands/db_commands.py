import asyncio

import typer

from common.utils.utils import get_logger
from shared_db.db.init_db import init_db
from shared_db.db.populate_db import populate_db
from shared_db.db.run_migrations import run_migrations

# Get logger for this module
logger = get_logger(__name__)

# Create a Typer app
app = typer.Typer(help="Database management commands")


@app.command()
def init() -> None:
    """Initialize the database by creating all tables."""
    logger.info("Initializing database...")
    asyncio.run(init_db())
    logger.info("Database initialized successfully!")


@app.command()
def migrate() -> None:
    """Run database migrations using Alembic."""
    logger.info("Running database migrations...")
    success = run_migrations()
    if success:
        logger.info("Database migrations completed successfully!")
    else:
        logger.error("Database migrations failed!")
        raise typer.Exit(code=1)


@app.command()
def populate() -> None:
    """Populate the database with sample data."""
    logger.info("Populating database...")
    # Initialize the database first to ensure tables exist
    asyncio.run(init_db())
    # Then populate it
    populate_db()
    logger.info("Database populated successfully!")


@app.command()
def setup() -> None:
    """Complete database setup: run migrations and populate with sample data."""
    logger.info("Setting up database...")
    # Run migrations first
    success = run_migrations()
    if not success:
        logger.error("Database migrations failed!")
        raise typer.Exit(code=1)

    # Then populate with sample data
    populate_db()
    logger.info("Database setup completed successfully!")


if __name__ == "__main__":
    app()
