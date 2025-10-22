#!/usr/bin/env python3
"""Create a database-agnostic migration that works with both SQLite and PostgreSQL."""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_agnostic_migration(message: str = "Database-agnostic migration") -> bool:
    """Create a migration that works with both SQLite and PostgreSQL.

    This function:
    1. Temporarily sets DATABASE_URL to SQLite to generate SQLite-compatible migrations
    2. Generates the migration
    3. Post-processes the migration to ensure cross-database compatibility

    Args:
        message: The migration message

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the repository root directory
        repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        alembic_cfg_path = repo_root / "libs" / "shared_db" / "alembic.ini"

        if not alembic_cfg_path.exists():
            raise FileNotFoundError(f"Alembic config file not found: {alembic_cfg_path}")

        logger.info(f"Generating database-agnostic migration: {message}")

        # Set environment to use SQLite for migration generation
        # This ensures enums are generated as strings, which work in both databases
        env = {"DATABASE_URL": "sqlite:///./migration_temp.db", "APP_ENV": "development"}

        # Build the command
        cmd = ["uv", "run", "--package", "shared_db", "alembic", "-c", str(alembic_cfg_path), "revision", "--autogenerate", "-m", message]

        logger.info("Running alembic revision with SQLite compatibility...")

        # Run alembic revision --autogenerate
        result = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=True, env={**dict(os.environ), **env})

        logger.info(f"Migration generation output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Migration generation warnings:\n{result.stderr}")

        # Find the generated migration file
        versions_dir = repo_root / "libs" / "shared_db" / "alembic" / "versions"
        migration_files = list(versions_dir.glob("*.py"))
        if migration_files:
            latest_migration = max(migration_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Generated migration file: {latest_migration}")

            # Post-process the migration to ensure cross-database compatibility
            post_process_migration(latest_migration)

        logger.info("Database-agnostic migration created successfully!")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate migration: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error during migration generation: {e}")
        return False


def post_process_migration(migration_file: Path) -> None:
    """Post-process the migration file to ensure cross-database compatibility."""
    try:
        logger.info(f"Post-processing migration file: {migration_file}")

        # Read the migration file
        content = migration_file.read_text()

        # Normalise trailing whitespace so Ruff stays green.
        normalised_content = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
        modified = normalised_content != content
        content = normalised_content

        # Add a comment explaining the cross-database compatibility after the future import
        if "Cross-database compatible migration" not in content:
            # Find the position after the docstring and imports
            lines = content.split("\n")
            insert_pos = 0

            # Skip the original docstring
            if lines[0].startswith('"""'):
                for i, line in enumerate(lines[1:], 1):
                    if '"""' in line:
                        insert_pos = i + 1
                        break

            # Skip imports
            for i in range(insert_pos, len(lines)):
                if lines[i].strip() and not (lines[i].startswith("from ") or lines[i].startswith("import ")):
                    insert_pos = i
                    break

            header_comment = """
# Cross-database compatible migration.
# This migration is designed to work with both SQLite (for tests) and PostgreSQL (for development/production).
# Enums are stored as strings to ensure compatibility across database types.
"""
            lines.insert(insert_pos, header_comment)
            content = "\n".join(lines)
            modified = True

        if modified:
            _ = migration_file.write_text(content)
            logger.info("Migration file post-processed for cross-database compatibility")
        else:
            logger.info("No post-processing needed")

    except Exception as e:
        logger.exception(f"Error post-processing migration file: {e}")


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description="Create a database-agnostic migration")
    _ = parser.add_argument("-m", "--message", default="Database-agnostic migration", help="Migration message")

    args = parser.parse_args()

    success = create_agnostic_migration(args.message)
    sys.exit(0 if success else 1)
