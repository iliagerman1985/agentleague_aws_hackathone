import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from common.utils.utils import get_logger

# Get logger for this module
logger = get_logger(__name__)


def run_migrations() -> bool | None:
    """Run database migrations using Alembic.
    This function uses the database URL from the config service via alembic/env.py.
    """
    try:
        # Get the path to the repository root directory
        # Path: /workspaces/agentleague/libs/shared_db/shared_db/db/run_migrations.py
        # We need to go up 5 levels: db -> shared_db -> shared_db -> libs -> agentleague
        repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        alembic_cfg_path = repo_root / "libs" / "shared_db" / "alembic.ini"

        logger.info("Starting database migrations", operation="run_migrations")

        # Use Alembic API directly instead of subprocess
        alembic_cfg = Config(str(alembic_cfg_path))

        # The alembic.ini already has script_location = libs/shared_db/alembic
        # We just need to make sure the working directory is the repo root
        # Set the script location to an absolute path by resolving the relative path
        original_script_location = alembic_cfg.get_main_option("script_location")
        if original_script_location and not Path(original_script_location).is_absolute():
            absolute_script_location = repo_root / original_script_location
            alembic_cfg.set_main_option("script_location", str(absolute_script_location))

        # Run the upgrade command. Use 'head' (default single-head path).
        # Disable Alembic's internal logging config so it doesn't override our structured logging.
        alembic_cfg.attributes["configure_logger"] = False
        command.upgrade(alembic_cfg, "head")

        logger.info(
            "Database migrations completed successfully",
            operation="run_migrations",
            status="success",
        )
        return True
    except Exception as e:
        logger.exception(
            "Migration failed",
            operation="run_migrations",
            status="failed",
            error=str(e),
        )
        return False


if __name__ == "__main__":
    # This allows the script to be run directly
    success = run_migrations()
    sys.exit(0 if success else 1)
