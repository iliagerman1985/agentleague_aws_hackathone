from __future__ import annotations

import os
from enum import StrEnum

import structlog
from dotenv import load_dotenv

logger = structlog.stdlib.get_logger("environment")

load_dotenv()


class Deployment(StrEnum):
    PRODUCTION = "prod"
    DEVELOPMENT = "development"
    HACKATHON = "hackathon"
    LOCAL = "local"
    UNIT_TEST = "unit_test"

    @staticmethod
    def current() -> Deployment:
        return CurrentDeployment

    @staticmethod
    def is_cloud() -> bool:
        """Check if running in cloud environment (AWS)."""
        return CurrentDeployment in (
            Deployment.PRODUCTION,
            Deployment.DEVELOPMENT,
            Deployment.HACKATHON,
        )

    @staticmethod
    def is_prod() -> bool:
        """Check if running in production environment (legacy method)."""
        return CurrentDeployment == Deployment.PRODUCTION

    @staticmethod
    def is_local() -> bool:
        return CurrentDeployment in (Deployment.LOCAL, Deployment.UNIT_TEST)

    @staticmethod
    def inherits_from_deployment() -> Deployment | None:
        match CurrentDeployment:
            case Deployment.UNIT_TEST:
                return Deployment.LOCAL
            case _:
                return None

    @classmethod
    def all(cls) -> list[str]:
        return [member.value for member in cls]


# Set current environment from ENVIRONMENT variable, default to local
try:
    CurrentDeployment = Deployment(os.environ["APP_ENV"].lower())
except (KeyError, ValueError):
    logger.warning("ENVIRONMENT not set or invalid, defaulting to LOCAL")
    CurrentDeployment = Deployment.LOCAL
