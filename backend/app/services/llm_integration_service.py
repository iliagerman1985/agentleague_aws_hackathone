"""LLM Integration service layer for business logic operations."""

import time

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.encryption import decrypt_api_key, encrypt_api_key
from common.core.app_error import Errors
from common.core.litellm_service import LiteLLMService
from common.enums import LLMProvider
from common.exceptions import ModelValidationError
from common.ids import LLMIntegrationId, UserId
from common.model_config import ModelConfigFactory
from common.utils import JsonModel
from common.utils.utils import get_logger
from shared_db.crud.llm_integration import LLMIntegrationDAO
from shared_db.models.llm_enums import (
    AnthropicModel,
    AWSBedrockModel,
    GoogleModel,
    LLMModelType,
    OpenAIModel,
    get_default_model_for_provider,
)
from shared_db.schemas.llm_integration import (
    LLMIntegrationCreate,
    LLMIntegrationResponse,
    LLMIntegrationUpdate,
    LLMIntegrationWithKey,
    LLMModelInfo,
    LLMProviderModels,
    LLMTestResponse,
)

logger = get_logger()


# Provider model mappings (matching client/tests/constants/models.ts)
PROVIDER_MODELS: dict[LLMProvider, type[LLMModelType]] = {
    LLMProvider.OPENAI: OpenAIModel,
    LLMProvider.ANTHROPIC: AnthropicModel,
    LLMProvider.GOOGLE: GoogleModel,
    LLMProvider.AWS_BEDROCK: AWSBedrockModel,
}


class SystemProviderConfig(JsonModel):
    """Configuration for a system-wide LLM provider integration."""

    provider: LLMProvider = Field(..., description="LLM provider type")
    model: LLMModelType = Field(..., description="Model identifier for this provider")
    display_name: str = Field(..., description="Human-readable display name")
    config_key: str = Field(..., description="Configuration key path for API key in secrets.yaml")
    priority: int = Field(..., description="Priority order for default selection (lower is higher priority)")


class LLMIntegrationService:
    """Service layer for LLM integration operations.
    Handles business logic and coordinates between routers and DAOs.
    """

    def __init__(self, llm_integration_dao: LLMIntegrationDAO, litellm_service: LiteLLMService) -> None:
        """Initialize LLMIntegrationService with DAO dependency.

        Args:
            llm_integration_dao: LLMIntegrationDAO instance for database operations
            litellm_service: Optional LiteLLM service for API testing
        """
        self.llm_integration_dao = llm_integration_dao
        self._litellm_service = litellm_service

    async def get_user_integrations(
        self,
        db: AsyncSession,
        user_id: UserId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LLMIntegrationResponse]:
        """Get all LLM integrations for a user.

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LLMIntegrationResponse objects
        """
        logger.info(f"Getting LLM integrations for user: {user_id}")
        return await self.llm_integration_dao.get_by_user_id(db, user_id, skip=skip, limit=limit)

    async def get_user_integration_by_id(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
    ) -> LLMIntegrationResponse | None:
        """Get a specific LLM integration by ID (with user ownership check).

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID

        Returns:
            LLMIntegrationResponse if found and owned by user, None otherwise
        """
        logger.info(f"Getting LLM integration {integration_id} for user {user_id}")
        integration = await self.llm_integration_dao.get(db, integration_id)

        if not integration or integration.user_id != user_id:
            return None

        return integration

    async def get_user_default_integration(
        self,
        db: AsyncSession,
        user_id: UserId,
    ) -> LLMIntegrationResponse | None:
        """Get user's default LLM integration.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Default LLMIntegrationResponse if found, None otherwise
        """
        logger.info(f"Getting default LLM integration for user: {user_id}")
        return await self.llm_integration_dao.get_user_default_integration(db, user_id)

    async def require_user_default_integration(
        self,
        db: AsyncSession,
        user_id: UserId,
    ) -> LLMIntegrationResponse:
        """Require that the user has a default LLM integration configured.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Default LLMIntegrationResponse

        Raises:
            AppError: If no default LLM integration is configured
        """
        integration = await self.get_user_default_integration(db, user_id)
        if not integration:
            raise Errors.Llm.NOT_FOUND.create(
                "No default LLM integration configured. Please configure an LLM integration before creating games.", details={"user_id": user_id}
            )
        return integration

    async def get_user_integration_by_provider(
        self,
        db: AsyncSession,
        user_id: UserId,
        provider: LLMProvider,
    ) -> LLMIntegrationResponse | None:
        """Get the user's integration for a specific provider.

        Assumes at most one integration per provider per user (your constraint).
        """
        logger.info(f"Getting integration for user {user_id} and provider {provider}")
        return await self.llm_integration_dao.get_by_user_and_provider(db, user_id, provider)

    async def get_user_integration_by_provider_with_key(
        self,
        db: AsyncSession,
        user_id: UserId,
        provider: LLMProvider,
    ) -> LLMIntegrationWithKey | None:
        """Get the user's integration for a provider with decrypted API key."""
        integration = await self.get_user_integration_by_provider(db, user_id, provider)
        if not integration:
            return None
        return await self.get_integration_for_use(db, integration.id)

    async def create_integration(
        self,
        db: AsyncSession,
        user_id: UserId,
        integration_create: LLMIntegrationCreate,
    ) -> LLMIntegrationResponse:
        """Create a new LLM integration.

        Args:
            db: Database session
            user_id: User ID
            integration_create: Integration creation data

        Returns:
            Created LLMIntegrationResponse

        Raises:
            ValueError: If provider already exists for user or validation fails
        """
        logger.info(f"Creating LLM integration for user {user_id}, provider {integration_create.provider}")

        try:
            # Check if user already has an integration for this provider
            logger.info(f"Checking for existing integration for user {user_id}, provider {integration_create.provider}")
            existing = await self.llm_integration_dao.get_by_user_and_provider(db, user_id, integration_create.provider)
            if existing:
                logger.warning(f"Integration for provider '{integration_create.provider}' already exists for user {user_id}")
                raise ValueError(f"Integration for provider '{integration_create.provider}' already exists")

            # Validate the model for the provider
            logger.info(f"Validating model '{integration_create.selected_model}' for provider '{integration_create.provider}'")
            self._validate_model_for_provider(integration_create.provider, integration_create.selected_model)

            # Encrypt the API key
            logger.info("Encrypting API key")
            encrypted_key = encrypt_api_key(integration_create.api_key)
            logger.info("API key encrypted successfully")

            # Create integration with encrypted key
            logger.info("Preparing integration data for database")
            integration_data = integration_create.model_copy()
            integration_data.api_key = encrypted_key

            # If this is the user's first integration, make it default
            logger.info(f"Checking integration count for user {user_id}")
            user_integrations_count = await self.llm_integration_dao.get_count_by_user(db, user_id)
            logger.info(f"User {user_id} has {user_integrations_count} existing integrations")
            if user_integrations_count == 0:
                integration_data.is_default = True
                logger.info("Setting as default integration (first for user)")

            logger.info("Creating integration in database")
            result = await self.llm_integration_dao.create_with_user(db, obj_in=integration_data, user_id=user_id)
            logger.info(f"Successfully created integration with ID: {result.id}")
            return result

        except Exception:
            logger.exception("Error in create_integration")
            raise

    async def update_integration(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
        integration_update: LLMIntegrationUpdate,
    ) -> LLMIntegrationResponse | None:
        """Update an LLM integration.

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID
            integration_update: Integration update data

        Returns:
            Updated LLMIntegrationResponse if successful, None if not found

        Raises:
            ValueError: If validation fails
        """
        logger.info(f"Updating LLM integration {integration_id} for user {user_id}")

        # Get existing integration to validate provider-model compatibility
        existing = await self.get_user_integration_by_id(db, integration_id, user_id)
        if not existing:
            return None

        # Validate model if it's being updated
        if integration_update.selected_model:
            provider = LLMProvider(existing.provider)
            self._validate_model_for_provider(provider, integration_update.selected_model)

        # Encrypt API key if provided
        update_data = integration_update.model_copy()
        if integration_update.api_key:
            update_data.api_key = encrypt_api_key(integration_update.api_key)

        return await self.llm_integration_dao.update_by_id(db, integration_id, user_id, update_data)

    async def set_default_integration(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
    ) -> LLMIntegrationResponse | None:
        """Set an integration as the user's default.

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID

        Returns:
            Updated LLMIntegrationResponse if successful, None if not found
        """
        logger.info(f"Setting LLM integration {integration_id} as default for user {user_id}")
        return await self.llm_integration_dao.set_as_default(db, integration_id, user_id)

    async def delete_integration(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
    ) -> bool:
        """Delete an LLM integration.

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting LLM integration {integration_id} for user {user_id}")
        return await self.llm_integration_dao.delete_by_id(db, integration_id, user_id)

    async def get_integration_for_use(self, db: AsyncSession, integration_id: LLMIntegrationId) -> LLMIntegrationWithKey:
        """Get integration with decrypted API key for use.

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID

        Returns:
            LLMIntegrationWithKey with decrypted API key, or None if not found
        """
        logger.info(f"Getting LLM integration {integration_id} with key")

        integration_with_encrypted_key = await self.llm_integration_dao.get_with_decrypted_key(db, integration_id)
        if not integration_with_encrypted_key:
            raise Errors.Llm.NOT_FOUND.create(f"LLM integration not found: {integration_id}", details={"integration_id": integration_id})

        # Decrypt the API key
        decrypted_key = decrypt_api_key(integration_with_encrypted_key.api_key)
        integration_with_encrypted_key.api_key = decrypted_key
        return integration_with_encrypted_key

    async def test_integration(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        test_prompt: str = "Hello, please respond with 'API connection successful'",
    ) -> LLMTestResponse:
        """Test an LLM integration by making a simple API call.

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID
            test_prompt: Test prompt to send

        Returns:
            LLMTestResponse with test results
        """
        logger.info(f"Testing LLM integration {integration_id}")

        start_time = time.time()

        try:
            # Get integration with decrypted key
            integration = await self.get_integration_for_use(db, integration_id)
            if not integration:
                return LLMTestResponse(
                    success=False,
                    error_message="Integration not found or access denied",
                )

            # Test the integration using LiteLLM service
            provider = LLMProvider(integration.provider)

            # Use LiteLLM service for testing
            test_success = await self._litellm_service.test_connection(
                provider=provider,
                model=integration.selected_model,
                api_key=integration.api_key,
                test_message=test_prompt,
            )

            if not test_success:
                raise Exception("API connection test failed")

            response_text = "API connection successful"

            latency_ms = int((time.time() - start_time) * 1000)

            return LLMTestResponse(
                success=True,
                response_text=response_text,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.exception("LLM integration test failed")
            latency_ms = int((time.time() - start_time) * 1000)

            return LLMTestResponse(
                success=False,
                error_message=str(e),
                latency_ms=latency_ms,
            )

    async def test_api_key_directly(self, provider: LLMProvider, api_key: str, model: str, test_prompt: str) -> LLMTestResponse:
        """Test an API key directly without saving an integration.

        Args:
            provider: LLM provider
            api_key: Plain text API key
            model: Model to test with
            test_prompt: Test prompt to send

        Returns:
            LLMTestResponse with test results
        """
        logger.info(f"Testing API key directly for provider: {provider}, model: {model}")

        start_time = time.time()

        try:
            # Validate the model for the provider
            self._validate_model_for_provider(provider, model)

            # Test the API key using LiteLLM service
            typed_model = self._to_llm_model_type(provider, model)
            test_success = await self._litellm_service.test_connection(
                provider=provider,
                model=typed_model,
                api_key=api_key,
                test_message=test_prompt,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if test_success:
                return LLMTestResponse(success=True, response_text="API connection successful", latency_ms=latency_ms)
            else:
                return LLMTestResponse(success=False, error_message="API connection test failed", latency_ms=latency_ms)

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"API key test failed for provider {provider}")

            return LLMTestResponse(success=False, error_message=str(e), latency_ms=latency_ms)

    def get_available_models(self, provider: LLMProvider | None = None) -> list[LLMProviderModels]:
        """Get available models for a provider or all providers.

        Args:
            provider: Optional provider to filter by

        Returns:
            List of LLMProviderModels with model information
        """
        if provider:
            configs = ModelConfigFactory.get_configs_for_provider(provider)
            return [
                LLMProviderModels(
                    provider=provider,
                    models=[
                        LLMModelInfo(
                            model_id=config.model_id,
                            display_name=config.display_name,
                            description=f"{config.display_name} - {config.context_window:,} token context",
                            context_window=config.context_window,
                            supports_tools=config.supports_tools,
                            supports_vision=config.supports_vision,
                            input_price_per_1m=config.input_price_per_1m,
                            output_price_per_1m=config.output_price_per_1m,
                        )
                        for config in configs
                    ],
                )
            ]

        # Get models for all providers
        result: list[LLMProviderModels] = []
        for prov in LLMProvider:
            configs = ModelConfigFactory.get_configs_for_provider(prov)
            if configs:
                result.append(
                    LLMProviderModels(
                        provider=prov,
                        models=[
                            LLMModelInfo(
                                model_id=config.model_id,
                                display_name=config.display_name,
                                description=f"{config.display_name} - {config.context_window:,} token context",
                                context_window=config.context_window,
                                supports_tools=config.supports_tools,
                                supports_vision=config.supports_vision,
                                input_price_per_1m=config.input_price_per_1m,
                                output_price_per_1m=config.output_price_per_1m,
                            )
                            for config in configs
                        ],
                    )
                )
        return result

    async def create_system_integrations_for_user(self, db: AsyncSession, user_id: UserId) -> list[LLMIntegrationResponse]:
        """Create system LLM integrations for a new user using credentials from secrets.yaml.

        This method automatically provisions all available LLM integrations for a user
        using the system-wide API keys from configuration. This is called when a new user
        is created (e.g., via OAuth signup). Only one integration per provider is allowed.

        Args:
            db: Database session
            user_id: User ID to create integrations for

        Returns:
            List of created LLMIntegrationResponse objects
        """
        from common.core.config_service import ConfigService

        logger.info(f"Creating system LLM integrations for user {user_id}")
        config_service = ConfigService()
        created_integrations: list[LLMIntegrationResponse] = []

        # Provider display names
        provider_display_names: dict[LLMProvider, str] = {
            LLMProvider.AWS_BEDROCK: "AWS Bedrock",
            LLMProvider.GOOGLE: "Google Gemini",
            LLMProvider.OPENAI: "OpenAI",
            LLMProvider.ANTHROPIC: "Anthropic",
        }

        # Define provider priority order (lower number = higher priority)
        provider_priority_order: list[LLMProvider] = [
            LLMProvider.AWS_BEDROCK,
            LLMProvider.GOOGLE,
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
        ]

        # Generate provider configurations with priority order (using default fast models)
        provider_configs: list[SystemProviderConfig] = [
            SystemProviderConfig(
                provider=provider,
                model=get_default_model_for_provider(provider),
                display_name=provider_display_names[provider],
                config_key=f"llm_providers.{provider.value}.api_key",
                priority=idx + 1,
            )
            for idx, provider in enumerate(provider_priority_order)
        ]

        # Create integration for each available provider
        first_integration = True
        for config in provider_configs:
            api_key = config_service.get(config.config_key)
            if not api_key:
                logger.info(f"Skipping {config.display_name} - no API key configured")
                continue

            try:
                # Check if user already has an integration for this provider
                existing = await self.llm_integration_dao.get_by_user_and_provider(db, user_id, config.provider)
                if existing:
                    logger.info(f"Skipping {config.display_name} - user {user_id} already has integration for this provider")
                    continue

                # Encrypt the API key
                encrypted_key = encrypt_api_key(api_key)

                # Convert model string to proper type
                typed_model = self._to_llm_model_type(config.provider, config.model)

                # Create integration
                integration_create = LLMIntegrationCreate(
                    provider=config.provider,
                    api_key=encrypted_key,  # Pass already encrypted key
                    selected_model=typed_model,
                    display_name=config.display_name,
                    is_active=True,
                    is_default=first_integration,  # First integration is default
                )

                # Manually set the encrypted key (skip encryption in create_integration)
                integration = await self.llm_integration_dao.create_with_user(
                    db,
                    obj_in=integration_create,
                    user_id=user_id,
                )

                created_integrations.append(integration)
                logger.info(f"Created {config.display_name} integration for user {user_id}")
                first_integration = False

            except Exception as e:
                logger.warning(f"Failed to create {config.display_name} integration for user {user_id}: {e}")
                continue

        if created_integrations:
            logger.info(f"Created {len(created_integrations)} system integrations for user {user_id}")
        else:
            logger.warning(f"No system integrations created for user {user_id}")

        return created_integrations

    def _validate_model_for_provider(self, provider: LLMProvider, model: str) -> None:
        """Validate that a model is supported for the given provider.

        Args:
            provider: LLM provider
            model: Model identifier

        Raises:
            ModelValidationError: If model is not supported for the provider
        """
        # Use ModelConfigFactory as single source of truth
        if not ModelConfigFactory.is_model_supported(model):
            # Get valid models for this provider from config factory
            configs = ModelConfigFactory.get_configs_for_provider(provider)
            valid_models = [config.model_id for config in configs]
            raise ModelValidationError(provider, model, valid_models)

    def _to_llm_model_type(self, provider: LLMProvider, model: str) -> LLMModelType:
        """Convert a raw model string to the provider's typed LLMModelType enum."""
        if provider == LLMProvider.OPENAI:
            return OpenAIModel(model)
        if provider == LLMProvider.ANTHROPIC:
            return AnthropicModel(model)
        if provider == LLMProvider.GOOGLE:
            return GoogleModel(model)
        if provider == LLMProvider.AWS_BEDROCK:
            return AWSBedrockModel(model)
        raise ValueError(f"Unsupported provider: {provider}")
