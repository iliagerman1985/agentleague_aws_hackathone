"""Populate test database with test users for testing purposes."""

import asyncio
import os
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from common.core.config_service import ConfigService
from common.core.service_factory import get_cognito_service
from common.enums import LLMProvider
from common.utils.utils import get_logger
from shared_db.db import AsyncSessionLocal, create_sync_session
from shared_db.models.llm_enums import AnthropicModel, AWSBedrockModel, GoogleModel, OpenAIModel
from shared_db.models.llm_integration import LLMIntegration
from shared_db.models.user import User, UserRole

logger = get_logger(__name__)

# Test users configuration
TEST_USERS = [
    # Mock Cognito test users (for flow testing)
    {
        "email": "admin@admin.com",
        "password": "Cowabunga2@",
        "full_name": "Test Admin User",
        "role": UserRole.ADMIN,
    },
    {
        "email": "user@test.com",
        "password": "TestPassword123!",
        "full_name": "Test Regular User",
        "role": UserRole.USER,
    },
    # Additional test users for future admin/non-admin scenarios
    {
        "email": "admin2@test.com",
        "password": "AdminPassword123!",
        "full_name": "Test Admin User 2",
        "role": UserRole.ADMIN,
    },
    {
        "email": "user2@test.com",
        "password": "UserPassword123!",
        "full_name": "Test Regular User 2",
        "role": UserRole.USER,
    },
    # Real Cognito test user (for real Cognito integration testing)
    {
        "email": "iliagerman@gmail.com",
        "password": "Cowabunga1!",
        "full_name": "Ilia German",
        "role": UserRole.USER,
    },
]


def create_cognito_test_user_sync(user_data: dict[str, Any]) -> str:
    """Create a test user in Cognito (real or mock) - synchronous version"""
    return asyncio.run(create_cognito_test_user(user_data))


def create_database_user_sync(db: Session, user_data: dict[str, Any], cognito_sub: str) -> User:
    """Create a user in the database - synchronous version"""
    try:
        # Check if user already exists
        existing_user = None
        try:
            result = db.execute(select(User).filter(User.email == user_data["email"]))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                logger.info(f"User {user_data['email']} already exists in database")
                return existing_user
        except Exception as e:
            # Table might not exist yet, which is fine - we'll create the user
            logger.debug(f"Could not check for existing user {user_data['email']} (table might not exist yet): {e}")
            existing_user = None

        # Create new user
        db_user = User(
            username=user_data["email"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            cognito_sub=cognito_sub,
            role=user_data["role"],
            is_active=True,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(
            f"✓ Created database user: {user_data['email']} ({user_data['role'].value})",
        )
        return db_user

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create database user {user_data['email']}: {e}")
        raise


def create_test_llm_integrations_sync(db: Session, user: User) -> list[LLMIntegration]:
    """Create test LLM integrations for all available providers - synchronous version"""
    import os

    from common.enums import LLMProvider

    # Check if LLM integration creation should be skipped
    skip_llm_integrations = os.getenv("SKIP_TEST_LLM_INTEGRATIONS", "false").lower() in ("true", "1", "yes")
    if skip_llm_integrations:
        logger.info("Skipping test LLM integrations creation (SKIP_TEST_LLM_INTEGRATIONS=true)")
        return []

    # Skip LLM integrations for the CRUD test user to ensure clean test state
    if str(user.email) == "admin@admin.com":
        logger.info(f"Skipping LLM integrations for CRUD test user: {user.email}")
        return []

    created_integrations: list[LLMIntegration] = []
    config_service = ConfigService()

    # Provider to model mapping
    provider_models = {
        LLMProvider.OPENAI: OpenAIModel.FAST.value,
        LLMProvider.ANTHROPIC: AnthropicModel.FAST.value,
        LLMProvider.GOOGLE: GoogleModel.FAST.value,
        LLMProvider.AWS_BEDROCK: AWSBedrockModel.FAST.value,
    }

    for provider, default_model in provider_models.items():
        try:
            # Check if user already has integration for this provider
            result = db.execute(select(LLMIntegration).filter(LLMIntegration.user_id == user.id, LLMIntegration.provider == provider))
            existing_integration = result.scalar_one_or_none()

            if existing_integration:
                logger.info(f"User {user.email} already has {provider.value} integration")
                created_integrations.append(existing_integration)
                continue

            # Get provider configuration
            provider_config = config_service.get_provider_config(provider.value)
            if not provider_config or not provider_config.api_key:
                logger.info(f"No configuration found for {provider.value}, skipping")
                continue

            # Create integration for this provider
            # Type narrowed by the check above - we know api_key is not None
            integration = create_single_llm_integration_sync(db, user, provider, default_model, str(provider_config.api_key))
            if integration:
                created_integrations.append(integration)

        except Exception as e:
            logger.warning(f"Failed to create {provider.value} integration for {user.email}: {e}")
            continue

    # Set the first integration as default if no default exists
    if created_integrations:
        # Check if user has any default integration
        stmt = select(LLMIntegration).filter(
            LLMIntegration.user_id == user.id,
            LLMIntegration.is_default == True,  # noqa: E712
        )
        result = db.execute(stmt)
        existing_default = result.scalar_one_or_none()

        if not existing_default:
            # Set the first created integration as default
            first_integration = created_integrations[0]
            first_integration.is_default = True
            db.commit()
            logger.info(f"Set {first_integration.provider} as default for {user.email}")

    return created_integrations


def create_single_llm_integration_sync(db: Session, user: User, provider: LLMProvider, model: str, api_key: str) -> LLMIntegration | None:
    """Create a single LLM integration for a specific provider - synchronous version."""
    try:
        # Import the encryption service from backend
        import os
        import sys

        backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend")
        sys.path.insert(0, backend_path)
        from app.utils.encryption import encrypt_api_key

        encrypted_key = encrypt_api_key(api_key)

        integration = LLMIntegration(
            user_id=user.id,
            provider=provider.value,
            api_key_encrypted=encrypted_key,
            selected_model=model,
            display_name=f"Test {provider.value.title()} Integration",
            is_active=True,
            is_default=False,  # Will be set later if needed
        )

        db.add(integration)
        db.commit()
        db.refresh(integration)

        logger.info(f"✓ Created {provider.value} integration for user: {user.email}")
        return integration

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create {provider.value} integration for {user.email}: {e}")
        return None


def populate_test_db_sync() -> bool | None:
    """Populate test database with test users - synchronous version"""
    config_service = ConfigService()

    # Debug logging to see environment configuration
    logger.info(f"Environment variables - USE_MOCK_COGNITO: {os.getenv('USE_MOCK_COGNITO')}")
    logger.info(f"Environment variables - APP_ENV: {os.getenv('APP_ENV')}")
    logger.info(f"Config service - is_testing(): {config_service.is_testing()}")
    logger.info(f"Config service - use_mock_cognito(): {config_service.use_mock_cognito()}")

    if not config_service.is_testing():
        logger.error("This script should only be run in test environment")
        return False

    logger.info("Populating test database with test users")

    db = create_sync_session()
    try:
        created_users: list[User] = []
        for user_data in TEST_USERS:
            try:
                # Create user in Cognito (real or mock)
                cognito_sub = create_cognito_test_user_sync(user_data)

                # Create user in database
                db_user = create_database_user_sync(db, user_data, cognito_sub)
                created_users.append(db_user)

                # Create test LLM integrations for all available providers
                integrations = create_test_llm_integrations_sync(db, db_user)
                logger.info(f"Created {len(integrations)} LLM integrations for {user_data['email']}")

                logger.info(
                    f"✓ Created complete user: {user_data['email']} (Cognito + DB + LLM)",
                )

            except Exception as e:
                logger.exception(f"Error creating test user {user_data['email']}: {e}")
                # Continue with other users
                continue

        logger.info(f"Successfully created {len(created_users)} test users")

        # If using mock Cognito, log that we're using database-backed authentication
        if config_service.use_mock_cognito():
            logger.info(
                "Mock Cognito service configured to use database for authentication",
            )

        return True

    except Exception as e:
        db.rollback()
        logger.exception(f"Error populating test database: {e}")
        return False
    finally:
        db.close()


async def create_cognito_test_user(user_data: dict[str, Any]) -> str:
    """Create a test user in Cognito (real or mock)"""
    config_service = ConfigService()
    cognito_service = get_cognito_service()

    # Debug logging to see which service is being used
    logger.info(f"USE_MOCK_COGNITO environment variable: {os.getenv('USE_MOCK_COGNITO')}")
    logger.info(f"Config service use_mock_cognito(): {config_service.use_mock_cognito()}")
    logger.info(f"Cognito service type: {type(cognito_service).__name__}")

    try:
        # Check if user already exists (for mock service only)
        if config_service.use_mock_cognito():
            # Mock service has user_exists method
            if hasattr(cognito_service, "user_exists") and await cognito_service.user_exists(user_data["email"]):
                logger.info(f"User {user_data['email']} already exists in Cognito")
                # For mock, return deterministic user_sub
                import hashlib

                email_hash = hashlib.md5(user_data["email"].encode()).hexdigest()[:8]
                return f"mock-user-{email_hash}"

        # Create new user
        cognito_response = await cognito_service.sign_up(
            email=user_data["email"],
            password=user_data["password"],
            full_name=user_data["full_name"],
        )

        user_sub = cognito_response["user_sub"]
        logger.info(f"✓ Created Cognito user: {user_data['email']} (sub: {user_sub})")
        return user_sub

    except Exception as e:
        logger.exception(f"Failed to create Cognito user {user_data['email']}: {e}")
        raise


async def create_test_llm_integrations(db: AsyncSession, user: User) -> list[LLMIntegration]:
    """Create test LLM integrations for all available providers."""
    import os

    from common.enums import LLMProvider

    # Check if LLM integration creation should be skipped
    skip_llm_integrations = os.getenv("SKIP_TEST_LLM_INTEGRATIONS", "false").lower() in ("true", "1", "yes")
    if skip_llm_integrations:
        logger.info("Skipping test LLM integrations creation (SKIP_TEST_LLM_INTEGRATIONS=true)")
        return []

    # Skip LLM integrations for the CRUD test user to ensure clean test state
    if str(user.email) == "admin@admin.com":
        logger.info(f"Skipping LLM integrations for CRUD test user: {user.email}")
        return []

    created_integrations: list[LLMIntegration] = []
    config_service = ConfigService()

    # Provider to model mapping
    provider_models = {
        LLMProvider.OPENAI: OpenAIModel.FAST.value,
        LLMProvider.ANTHROPIC: AnthropicModel.FAST.value,
        LLMProvider.GOOGLE: GoogleModel.FAST.value,
        LLMProvider.AWS_BEDROCK: AWSBedrockModel.FAST.value,
    }

    for provider, default_model in provider_models.items():
        try:
            # Check if user already has integration for this provider
            result = await db.execute(select(LLMIntegration).filter(LLMIntegration.user_id == user.id, LLMIntegration.provider == provider))
            existing_integration = result.scalar_one_or_none()

            if existing_integration:
                logger.info(f"User {user.email} already has {provider.value} integration")
                created_integrations.append(existing_integration)
                continue

            # Get provider configuration
            provider_config = config_service.get_provider_config(provider.value)
            if not provider_config or not provider_config.api_key:
                logger.info(f"No configuration found for {provider.value}, skipping")
                continue

            # Create integration for this provider
            # Type narrowed by the check above - we know api_key is not None
            integration = await create_single_llm_integration(db, user, provider, default_model, str(provider_config.api_key))
            if integration:
                created_integrations.append(integration)

        except Exception as e:
            logger.warning(f"Failed to create {provider.value} integration for {user.email}: {e}")
            continue

    # Set the first integration as default if no default exists
    if created_integrations:
        # Check if user has any default integration
        stmt = select(LLMIntegration).filter(
            LLMIntegration.user_id == user.id,
            LLMIntegration.is_default == True,  # noqa: E712
        )
        result = await db.execute(stmt)
        existing_default = result.scalar_one_or_none()

        if not existing_default:
            # Set the first created integration as default
            first_integration = created_integrations[0]
            first_integration.is_default = True
            await db.commit()
            logger.info(f"Set {first_integration.provider} as default for {user.email}")

    return created_integrations


async def create_single_llm_integration(db: AsyncSession, user: User, provider: LLMProvider, model: str, api_key: str) -> LLMIntegration | None:
    """Create a single LLM integration for a specific provider."""
    try:
        # Import the encryption service from backend
        import os
        import sys

        backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend")
        sys.path.insert(0, backend_path)
        from app.utils.encryption import encrypt_api_key

        encrypted_key = encrypt_api_key(api_key)

        integration = LLMIntegration(
            user_id=user.id,
            provider=provider.value,
            api_key_encrypted=encrypted_key,
            selected_model=model,
            display_name=f"Test {provider.value.title()} Integration",
            is_active=True,
            is_default=False,  # Will be set later if needed
        )

        db.add(integration)
        await db.commit()
        await db.refresh(integration)

        logger.info(f"✓ Created {provider.value} integration for user: {user.email}")
        return integration

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create {provider.value} integration for {user.email}: {e}")
        return None


async def create_test_llm_integration(db: AsyncSession, user: User) -> LLMIntegration | None:
    """Create a test LLM integration for a user (legacy method for backward compatibility)."""
    integrations = await create_test_llm_integrations(db, user)
    return integrations[0] if integrations else None


async def create_legacy_openai_integration(db: AsyncSession, user: User) -> LLMIntegration | None:
    """Create legacy OpenAI integration (fallback method)."""
    try:
        from sqlalchemy import select

        # Check if user already has an LLM integration
        result = await db.execute(select(LLMIntegration).filter(LLMIntegration.user_id == user.id))
        existing_integration = result.scalar_one_or_none()

        if existing_integration:
            logger.info(f"User {user.email} already has an LLM integration")
            return existing_integration

        # Create a test OpenAI integration with a properly encrypted real API key
        # Use the actual encryption service to encrypt the real OpenAI API key from secrets
        try:
            # Import the encryption service from backend
            import os
            import sys

            backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend")
            sys.path.insert(0, backend_path)
            from app.utils.encryption import encrypt_api_key

            # Get the real OpenAI API key from config service using new structure
            config_service = ConfigService()

            # Try new structure first
            real_api_key: str | None = None
            try:
                provider_config = config_service.get_provider_config("openai")
                if provider_config and provider_config.api_key:
                    real_api_key = str(provider_config.api_key)
            except Exception:
                pass

            # Fallback to legacy format
            if not real_api_key:
                legacy_api_key = config_service.get("openai.api_key")
                if legacy_api_key:
                    real_api_key = str(legacy_api_key)

            if not real_api_key:
                logger.error("❌ No OpenAI API key found in secrets.yaml - tests will fail!")
                logger.error("Please add a valid OpenAI API key to libs/common/secrets.yaml under 'llm_providers.openai.api_key' or 'openai.api_key'")
                raise ValueError("OpenAI API key is required for LLM integration tests")

            encrypted_key = encrypt_api_key(real_api_key)
            logger.info("✅ Successfully encrypted real OpenAI API key for testing")
        except ValueError as e:
            # Re-raise ValueError (missing API key) to fail immediately
            raise e
        except Exception as e:
            logger.error(f"❌ Failed to encrypt API key: {e}")
            logger.error("This indicates a configuration or encryption service issue")
            raise RuntimeError(f"Failed to create test LLM integration: {e}") from e

        test_integration = LLMIntegration(
            user_id=user.id,
            provider=LLMProvider.OPENAI.value,
            api_key_encrypted=encrypted_key,  # Properly encrypted dummy key for testing
            selected_model=OpenAIModel.FAST.value,
            display_name="Test OpenAI Integration",
            is_active=True,
            is_default=True,
        )

        db.add(test_integration)
        await db.commit()
        await db.refresh(test_integration)

        logger.info(f"✓ Created test LLM integration for user: {user.email}")
        return test_integration

    except Exception as e:
        await db.rollback()
        # Check if it's a unique constraint violation (integration already exists)
        if "unique" in str(e).lower() or "constraint" in str(e).lower():
            logger.info(f"LLM integration already exists for user {user.email} (constraint violation)")
            # Try to return the existing integration
            from sqlalchemy import select

            result = await db.execute(select(LLMIntegration).filter(LLMIntegration.user_id == user.id))
            existing_integration = result.scalar_one_or_none()
            return existing_integration
        else:
            logger.exception(f"Failed to create test LLM integration for user {user.email}: {e}")
            return None


async def create_database_user(db: AsyncSession, user_data: dict[str, Any], cognito_sub: str) -> User:
    """Create a user in the database"""
    try:
        # Check if user already exists (handle case where table doesn't exist yet)
        existing_user = None
        try:
            result = await db.execute(select(User).filter(User.email == user_data["email"]))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                logger.info(f"User {user_data['email']} already exists in database")
                return existing_user
        except Exception as e:
            # Table might not exist yet, which is fine - we'll create the user
            logger.debug(f"Could not check for existing user {user_data['email']} (table might not exist yet): {e}")
            existing_user = None

        # Create new user
        db_user = User(
            username=user_data["email"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            cognito_sub=cognito_sub,
            role=user_data["role"],
            is_active=True,
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        logger.info(
            f"✓ Created database user: {user_data['email']} ({user_data['role'].value})",
        )
        return db_user

    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to create database user {user_data['email']}: {e}")
        raise


async def populate_test_db() -> bool | None:
    """Populate test database with test users"""
    config_service = ConfigService()

    # Debug logging to see environment configuration
    logger.info(f"Environment variables - USE_MOCK_COGNITO: {os.getenv('USE_MOCK_COGNITO')}")
    logger.info(f"Environment variables - APP_ENV: {os.getenv('APP_ENV')}")
    logger.info(f"Config service - is_testing(): {config_service.is_testing()}")
    logger.info(f"Config service - use_mock_cognito(): {config_service.use_mock_cognito()}")

    if not config_service.is_testing():
        logger.error("This script should only be run in test environment")
        return False

    logger.info("Populating test database with test users")

    async with AsyncSessionLocal() as db:
        try:
            created_users: list[User] = []
            for user_data in TEST_USERS:
                try:
                    # Create user in Cognito (real or mock)
                    cognito_sub = await create_cognito_test_user(user_data)

                    # Create user in database
                    db_user = await create_database_user(db, user_data, cognito_sub)
                    created_users.append(db_user)

                    # Create test LLM integrations for all available providers
                    integrations = await create_test_llm_integrations(db, db_user)
                    logger.info(f"Created {len(integrations)} LLM integrations for {user_data['email']}")

                    logger.info(
                        f"✓ Created complete user: {user_data['email']} (Cognito + DB + LLM)",
                    )

                except Exception as e:
                    logger.exception(f"Error creating test user {user_data['email']}: {e}")
                    # Continue with other users
                    continue

            logger.info(f"Successfully created {len(created_users)} test users")

            # If using mock Cognito, log that we're using database-backed authentication
            if config_service.use_mock_cognito():
                logger.info(
                    "Mock Cognito service configured to use database for authentication",
                )

            return True

        except Exception as e:
            await db.rollback()
            logger.exception(f"Error populating test database: {e}")
            return False


def populate_test_db_wrapper():
    """Synchronous wrapper for populate_test_db"""
    return populate_test_db_sync()


if __name__ == "__main__":
    # This allows the script to be run directly
    success = populate_test_db_wrapper()
    if success:
        logger.info("Test database populated successfully!")
        sys.exit(0)
    else:
        logger.error("Failed to populate test database")
        sys.exit(1)
