"""LLM Integration API routes for managing user API keys and model selections."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_admin_user, get_current_user, get_db, get_llm_integration_service
from app.services.llm_integration_service import LLMIntegrationService
from common.core.logging_service import get_logger
from common.enums import LLMProvider
from common.ids import LLMIntegrationId
from shared_db.schemas.llm_integration import (
    LLMApiKeyTestRequest,
    LLMIntegrationCreate,
    LLMIntegrationResponse,
    LLMIntegrationUpdate,
    LLMProviderModels,
    LLMTestRequest,
    LLMTestResponse,
)
from shared_db.schemas.user import UserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/llm-integrations", tags=["LLM Integrations"])


@router.get("/")
async def get_user_llm_integrations(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> list[LLMIntegrationResponse]:
    """Get all LLM integrations for the current user."""
    return await service.get_user_integrations(db, current_user.id)


@router.get("/{integration_id}")
async def get_llm_integration(
    integration_id: LLMIntegrationId,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMIntegrationResponse:
    """Get a specific LLM integration by ID."""
    integration = await service.get_user_integration_by_id(db, integration_id, current_user.id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM integration not found")
    return integration


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_llm_integration(
    integration_data: LLMIntegrationCreate,
    current_user: Annotated[UserResponse, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMIntegrationResponse:
    """Create a new LLM integration. Admin only."""

    try:
        logger.info(f"Creating LLM integration for user {current_user.id} with data: {integration_data.model_dump(exclude={'api_key'})}")
        result = await service.create_integration(db, current_user.id, integration_data)
        logger.info(f"Successfully created LLM integration with ID: {result.id}")
        return result
    except ValueError as e:
        logger.exception("Validation error creating LLM integration")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error creating LLM integration: {e!s}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create LLM integration: {e!s}")


@router.put("/{integration_id}")
async def update_llm_integration(
    integration_id: LLMIntegrationId,
    integration_data: LLMIntegrationUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMIntegrationResponse:
    """Update an existing LLM integration. Admin only."""
    try:
        integration = await service.update_integration(db, integration_id, current_user.id, integration_data)
        if not integration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM integration not found")
        return integration
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update LLM integration")


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_integration(
    integration_id: LLMIntegrationId,
    current_user: Annotated[UserResponse, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> None:
    """Delete an LLM integration. Admin only."""
    success = await service.delete_integration(db, integration_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM integration not found")


@router.post("/{integration_id}/set-default")
async def set_default_integration(
    integration_id: LLMIntegrationId,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMIntegrationResponse:
    """Set an integration as the user's default."""
    integration = await service.set_default_integration(db, integration_id, current_user.id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM integration not found")
    return integration


@router.post("/{integration_id}/test")
async def test_llm_integration(
    integration_id: LLMIntegrationId,
    test_request: LLMTestRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMTestResponse:
    """Test an LLM integration with a sample request."""
    try:
        return await service.test_integration(db, integration_id, test_request.test_prompt)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to test integration: {e!s}")


@router.post("/test-api-key")
async def test_api_key(
    test_request: LLMApiKeyTestRequest,
    current_user: Annotated[UserResponse, Depends(get_current_admin_user)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMTestResponse:
    """Test an API key directly without saving an integration. Admin only."""
    try:
        provider = LLMProvider(test_request.provider)

        return await service.test_api_key_directly(provider, test_request.api_key, test_request.model, test_request.test_prompt)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to test API key: {e!s}")


@router.get("/providers/models")
async def get_available_models(
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> list[LLMProviderModels]:
    """Get all available models grouped by provider."""
    return service.get_available_models()


@router.get("/default")
async def get_default_integration(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> LLMIntegrationResponse:
    """Get the user's default LLM integration."""
    integration = await service.get_user_default_integration(db, current_user.id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No default LLM integration found")
    return integration
