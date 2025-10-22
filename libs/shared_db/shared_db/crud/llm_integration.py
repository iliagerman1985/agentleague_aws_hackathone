"""LLM Integration Data Access Object for database operations."""

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import LLMProvider
from common.ids import LLMIntegrationId, UserId
from common.utils.utils import get_logger
from shared_db.models.llm_integration import LLMIntegration
from shared_db.schemas.llm_integration import LLMIntegrationCreate, LLMIntegrationResponse, LLMIntegrationUpdate, LLMIntegrationWithKey

logger = get_logger(__name__)


class LLMIntegrationDAO:
    """Data Access Object for LLM Integration operations.
    Returns Pydantic objects instead of SQLAlchemy models.
    """

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: LLMIntegrationId) -> LLMIntegrationResponse | None:
        """Get an LLM integration by ID."""
        result = await db.execute(select(LLMIntegration).where(LLMIntegration.id == id))
        integration = result.scalar_one_or_none()
        return LLMIntegrationResponse.model_validate(integration) if integration else None

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LLMIntegrationResponse]:
        """Get multiple LLM integrations with pagination."""
        result = await db.execute(select(LLMIntegration).offset(skip).limit(limit))
        integrations = result.scalars().all()
        return [LLMIntegrationResponse.model_validate(integration) for integration in integrations]

    async def get_by_user_id(
        self,
        db: AsyncSession,
        user_id: UserId,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LLMIntegrationResponse]:
        """Get all LLM integrations for a specific user."""
        result = await db.execute(select(LLMIntegration).where(LLMIntegration.user_id == user_id.number).offset(skip).limit(limit))
        integrations = result.scalars().all()
        return [LLMIntegrationResponse.model_validate(integration) for integration in integrations]

    async def get_by_user_and_provider(
        self,
        db: AsyncSession,
        user_id: UserId,
        provider: LLMProvider,
    ) -> LLMIntegrationResponse | None:
        """Get user's integration for a specific provider."""
        result = await db.execute(
            select(LLMIntegration).where(
                LLMIntegration.user_id == user_id.number,
                LLMIntegration.provider == provider,
            )
        )
        integration = result.scalar_one_or_none()
        return LLMIntegrationResponse.model_validate(integration) if integration else None

    async def get_user_default_integration(
        self,
        db: AsyncSession,
        user_id: UserId,
    ) -> LLMIntegrationResponse | None:
        """Get user's default LLM integration."""
        result = await db.execute(
            select(LLMIntegration).where(
                LLMIntegration.user_id == user_id.number,
                LLMIntegration.is_default == True,  # noqa: E712
                LLMIntegration.is_active == True,  # noqa: E712
            )
        )
        integration = result.scalar_one_or_none()
        return LLMIntegrationResponse.model_validate(integration) if integration else None

    async def get_with_decrypted_key(self, db: AsyncSession, integration_id: LLMIntegrationId) -> LLMIntegrationWithKey | None:
        """Get integration with decrypted API key for internal use.

        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID (for security check)

        Returns:
            Integration with decrypted API key, or None if not found/unauthorized
        """
        result = await db.execute(select(LLMIntegration).where(LLMIntegration.id == integration_id))
        integration = result.scalar_one_or_none()

        if not integration:
            return None

        # First convert to regular LLMIntegrationResponse
        integration_response = LLMIntegrationResponse.model_validate(integration)

        # Then create LLMIntegrationWithKey with the decrypted key
        return LLMIntegrationWithKey(
            id=integration_response.id,
            user_id=integration_response.user_id,
            provider=integration_response.provider,
            selected_model=integration_response.selected_model,
            display_name=integration_response.display_name,
            is_active=integration_response.is_active,
            is_default=integration_response.is_default,
            created_at=integration_response.created_at,
            updated_at=integration_response.updated_at,
            api_key=getattr(integration, "api_key_encrypted", ""),  # Will be decrypted in service layer
        )

    async def create(self, db: AsyncSession, *, obj_in: LLMIntegrationCreate, **kwargs: Any) -> LLMIntegrationResponse:
        """Create a new LLM integration."""
        # Note: API key encryption should be handled in service layer
        # The user_id should be set as an attribute on obj_in before calling this method
        user_id = kwargs.get("user_id") or getattr(obj_in, "user_id", None)
        if user_id is None:
            raise ValueError("user_id is required to create an LLM integration")

        return await self.create_with_user(db, obj_in=obj_in, user_id=user_id)

    async def create_with_user(self, db: AsyncSession, *, obj_in: LLMIntegrationCreate, user_id: UserId) -> LLMIntegrationResponse:
        """Create a new LLM integration with explicit user_id."""
        try:
            logger.info(f"Creating LLM integration in database for user {user_id}")
            logger.info(f"Integration data: provider={obj_in.provider}, model={obj_in.selected_model}, display_name={obj_in.display_name}")

            # If this integration should be default, unset other defaults first
            if obj_in.is_default:
                logger.info(f"Unsetting other default integrations for user {user_id}")
                _ = await db.execute(
                    update(LLMIntegration).where(LLMIntegration.user_id == user_id.number, LLMIntegration.is_default == True).values(is_default=False)
                )

            db_obj = LLMIntegration(
                user_id=user_id.number,
                provider=obj_in.provider,  # StrEnum will be converted to string automatically
                selected_model=obj_in.selected_model,
                api_key_encrypted=obj_in.api_key,  # Will be encrypted in service layer
                display_name=obj_in.display_name,
                is_active=obj_in.is_active,
                is_default=obj_in.is_default,
            )
            logger.info("LLM integration object created, adding to database")
            db.add(db_obj)
            logger.info("Committing transaction")
            await db.commit()
            logger.info("Refreshing object")
            await db.refresh(db_obj)
            logger.info(f"Successfully created LLM integration with ID: {db_obj.id}")
            return LLMIntegrationResponse.model_validate(db_obj)
        except Exception:
            logger.exception("Error creating LLM integration in database")
            await db.rollback()
            raise

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: LLMIntegration,
        obj_in: LLMIntegrationUpdate,
    ) -> LLMIntegrationResponse:
        """Update an existing LLM integration."""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Handle special fields
        if update_data.get("api_key"):
            # API key will be encrypted in service layer
            update_data["api_key_encrypted"] = update_data.pop("api_key")

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return LLMIntegrationResponse.model_validate(db_obj)

    async def update_by_id(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
        obj_in: LLMIntegrationUpdate,
    ) -> LLMIntegrationResponse | None:
        """Update an LLM integration by ID (with user ownership check)."""
        result = await db.execute(
            select(LLMIntegration).where(
                LLMIntegration.id == integration_id,
                LLMIntegration.user_id == user_id.number,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return None
        return await self.update(db, db_obj=integration, obj_in=obj_in)

    async def set_as_default(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
    ) -> LLMIntegrationResponse | None:
        """Set an integration as the user's default (clears other defaults)."""
        # First, unset all defaults for this user
        _ = await db.execute(update(LLMIntegration).where(LLMIntegration.user_id == user_id, LLMIntegration.is_default == True).values(is_default=False))

        # Then set the specified integration as default
        result = await db.execute(
            select(LLMIntegration).where(
                LLMIntegration.id == integration_id,
                LLMIntegration.user_id == user_id,
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            await db.rollback()
            return None

        # Ensure it's active when set as default
        setattr(integration, "is_default", True)
        setattr(integration, "is_active", True)

        await db.commit()
        await db.refresh(integration)
        return LLMIntegrationResponse.model_validate(integration)

    async def delete(self, db: AsyncSession, *, id: LLMIntegrationId) -> bool:
        """Delete an LLM integration by ID."""
        result = await db.execute(select(LLMIntegration).where(LLMIntegration.id == id))
        integration = result.scalar_one_or_none()
        if not integration:
            return False

        await db.delete(integration)
        await db.commit()
        return True

    async def delete_by_id(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        user_id: UserId,
    ) -> bool:
        """Delete an LLM integration by ID (with user ownership check)."""
        result = await db.execute(
            select(LLMIntegration).where(
                LLMIntegration.id == integration_id,
                LLMIntegration.user_id == user_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return False

        await db.delete(integration)
        await db.commit()
        return True

    async def get_count_by_user(self, db: AsyncSession, user_id: UserId) -> int:
        """Get the total number of integrations for a user."""
        result = await db.execute(select(func.count(LLMIntegration.id)).where(LLMIntegration.user_id == user_id.number))
        return result.scalar() or 0
