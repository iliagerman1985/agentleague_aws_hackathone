import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to allow importing app modules
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def generate_migration(message="") -> bool | None:
    """Generate a new Alembic migration.
    This function uses the database URL from the config service via alembic/env.py.

    Args:
        message: The migration message

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # We already have the backend_dir from above

        # Build the command
        cmd = ["alembic", "revision", "--autogenerate"]
        if message:
            cmd.extend(["-m", message])

        logger.info(f"Generating migration with message: {message or '(no message)'}")

        # Run alembic revision --autogenerate
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"Generation output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Generation warnings/errors:\n{result.stderr}")

        logger.info("Migration generation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.exception(f"Migration generation failed with error code {e.returncode}")
        logger.exception(f"Error output:\n{e.stderr}")
        return False
    except Exception as e:
        logger.exception(f"Error generating migration: {e}")
        return False


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate a new Alembic migration")
    parser.add_argument("message", nargs="?", default="", help="Migration message")
    args = parser.parse_args()

    # Generate the migration
    success = generate_migration(args.message)
    sys.exit(0 if success else 1)
