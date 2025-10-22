"""Development launcher for Uvicorn that ensures logging is configured before reload workers start."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from common.logging.setup_logging import setup_logging


def main() -> None:
    """Configure logging and delegate to uvicorn.run."""

    # Load environment variables BEFORE setting up logging
    env = os.getenv("APP_ENV", "local")
    base_dir = Path(__file__).resolve().parent.parent / "libs" / "common"
    if env == "local":
        env_file = base_dir / ".env.local"
    else:
        env_file = base_dir / f".env.{env}"
    if env_file.exists():
        _ = load_dotenv(env_file)

    setup_logging()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9998,
        reload=True,
        reload_dirs=[".", "../libs"],  # Watch current dir (backend) and libs
    )


if __name__ == "__main__":
    main()
