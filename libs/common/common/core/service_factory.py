"""Service factory for choosing between real and mock services based on configuration."""

import os

from common.core.config_service import ConfigService
from common.utils.utils import get_logger

logger = get_logger(__name__)

# Initialize config service
config_service = ConfigService()


def get_cognito_service():
    """Factory function to get appropriate Cognito service"""
    config = ConfigService()
    logger.info(
        f"Cognito service resolution: USE_MOCK_COGNITO={os.getenv('USE_MOCK_COGNITO')} use_mock_cognito()={config.use_mock_cognito()} APP_ENV={os.getenv('APP_ENV')}"
    )
    if config.use_mock_cognito():
        logger.info("Using Mock Cognito Service for testing")
        from app.services.mock_cognito_service import MockCognitoService

        return MockCognitoService()
    logger.info("Using Real Cognito Service")
    from app.services.cognito_service import CognitoService

    return CognitoService()


def get_jwt_validator():
    """Factory function to get appropriate JWT validator"""
    if config_service.use_mock_cognito():
        logger.debug("Using Mock JWT Validator for testing")
        from common.core.mock_jwt_utils import mock_jwt_validator

        return mock_jwt_validator
    else:
        logger.debug("Using Real JWT Validator")
        from common.core.jwt_utils import jwt_validator

        return jwt_validator
