"""Avatar router for handling user and agent avatar uploads."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_agent_service, get_avatar_service, get_current_active_user, get_db, get_user_service
from app.schemas.avatar import AvatarResponse, AvatarUploadResponse, Theme
from app.services.agent_service import AgentService
from app.services.avatar_service import AvatarService
from app.services.user_service import UserService
from common.core.logging_service import get_logger
from common.ids import AgentId
from shared_db.models.user import AvatarType, User
from shared_db.schemas.agent import AgentUpdate
from shared_db.schemas.user import UserUpdate

logger = get_logger(__name__)

avatar_router = APIRouter()


from app.schemas.avatar import AgentAvatarInfo, BatchAgentAvatarRequest, BatchAgentAvatarResponse
from shared_db.crud.agent import AgentDAO, AgentVersionDAO


@avatar_router.post("/users/me/avatar")
async def upload_user_avatar(
    file: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
    crop_x: float | None = None,
    crop_y: float | None = None,
    crop_size: float | None = None,
    crop_scale: float | None = None,
    theme: Theme = Theme.DARK,
) -> AvatarUploadResponse:
    """Upload a new avatar for the current user."""
    try:
        # Parse crop data if provided
        crop_data = None
        if all(v is not None for v in [crop_x, crop_y, crop_size, crop_scale]):
            from app.schemas.avatar import CropData

            # Type narrowing - we know these are not None after the check
            assert crop_x is not None
            assert crop_y is not None
            assert crop_size is not None
            assert crop_scale is not None
            crop_data = CropData(x=crop_x, y=crop_y, size=crop_size, scale=crop_scale)

        # Determine background color based on theme
        background_color = (255, 255, 255) if theme == Theme.LIGHT else (31, 41, 55)  # white or gray-800

        # Process the uploaded image
        avatar_url, avatar_type = await avatar_service.process_uploaded_avatar(file, crop_data, background_color)

        # Update user avatar
        user_update = UserUpdate(avatar_url=avatar_url, avatar_type=avatar_type)

        _ = await user_service.update_user(db, current_user.id, user_update)

        logger.info(f"User {current_user.username} uploaded new avatar")
        return AvatarUploadResponse(message="Avatar uploaded successfully", avatar_url=avatar_url)

    except ValueError as e:
        logger.warning(f"Avatar upload validation error for user {current_user.username}: {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception(f"Failed to upload avatar for user {current_user.username}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload avatar")


@avatar_router.delete("/users/me/avatar")
async def reset_user_avatar(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
) -> AvatarUploadResponse:
    """Reset user avatar to default."""
    try:
        # Generate default avatar
        default_avatar_url = avatar_service.generate_default_avatar_url(current_user.username)

        # Update user with default avatar
        user_update = UserUpdate(avatar_url=default_avatar_url, avatar_type=AvatarType.DEFAULT)

        _ = await user_service.update_user(db, current_user.id, user_update)

        logger.info(f"User {current_user.username} reset avatar to default")
        return AvatarUploadResponse(message="Avatar reset successfully", avatar_url=default_avatar_url)

    except Exception:
        logger.exception(f"Failed to reset avatar for user {current_user.username}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset avatar")


@avatar_router.post("/agents/{agent_id}/avatar")
async def upload_agent_avatar(
    agent_id: AgentId,
    file: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
    crop_x: float | None = None,
    crop_y: float | None = None,
    crop_size: float | None = None,
    crop_scale: float | None = None,
    theme: Theme = Theme.DARK,
) -> AvatarUploadResponse:
    """Upload a new avatar for an agent."""
    try:
        # Get agent and verify ownership
        agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        # Parse crop data if provided
        crop_data = None
        if all(v is not None for v in [crop_x, crop_y, crop_size, crop_scale]):
            from app.schemas.avatar import CropData

            # Type narrowing - we know these are not None after the check
            assert crop_x is not None
            assert crop_y is not None
            assert crop_size is not None
            assert crop_scale is not None
            crop_data = CropData(x=crop_x, y=crop_y, size=crop_size, scale=crop_scale)

        # Determine background color based on theme
        background_color = (255, 255, 255) if theme == Theme.LIGHT else (31, 41, 55)  # white or gray-800

        # Process the uploaded image
        avatar_url, avatar_type = await avatar_service.process_uploaded_avatar(file, crop_data, background_color)

        # Update agent avatar
        agent_update = AgentUpdate(avatar_url=avatar_url, avatar_type=avatar_type)

        _ = await agent_service.update_agent(db, user_id=current_user.id, agent_id=agent_id, agent_in=agent_update)

        logger.info(f"User {current_user.username} uploaded avatar for agent {agent.name}")
        return AvatarUploadResponse(message="Agent avatar uploaded successfully", avatar_url=avatar_url)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Agent avatar upload validation error: {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception(f"Failed to upload avatar for agent {agent_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload agent avatar")


@avatar_router.delete("/agents/{agent_id}/avatar")
async def reset_agent_avatar(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
) -> AvatarUploadResponse:
    """Reset agent avatar to default."""
    try:
        # Get agent and verify ownership
        agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        # Generate default avatar
        default_avatar_url = avatar_service.generate_default_avatar_url(agent.name)

        # Update agent with default avatar
        agent_update = AgentUpdate(avatar_url=default_avatar_url, avatar_type=AvatarType.DEFAULT)

        _ = await agent_service.update_agent(db, user_id=current_user.id, agent_id=agent_id, agent_in=agent_update)

        logger.info(f"User {current_user.username} reset avatar for agent {agent.name}")
        return AvatarUploadResponse(message="Agent avatar reset successfully", avatar_url=default_avatar_url)

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to reset avatar for agent {agent_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset agent avatar")


@avatar_router.get("/users/me/avatar")
async def get_user_avatar(
    current_user: Annotated[User, Depends(get_current_active_user)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
) -> AvatarResponse:
    """Get current user's avatar URL."""
    if current_user.avatar_url:
        return AvatarResponse(avatar_url=current_user.avatar_url, avatar_type=current_user.avatar_type.value)
    else:
        # Generate default avatar
        default_avatar_url = avatar_service.generate_default_avatar_url(current_user.username)
        return AvatarResponse(avatar_url=default_avatar_url, avatar_type=AvatarType.DEFAULT.value)


@avatar_router.get("/agents/{agent_id}/avatar")
async def get_agent_avatar(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
) -> AvatarResponse:
    """Get agent's avatar URL."""
    try:
        agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        # Check if user owns the agent or if it's a system agent
        if agent.user_id != current_user.id and not agent.is_system:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this agent")

        if agent.avatar_url:
            return AvatarResponse(avatar_url=agent.avatar_url, avatar_type=agent.avatar_type.value if agent.avatar_type else AvatarType.DEFAULT.value)
        else:
            # Generate default avatar
            default_avatar_url = avatar_service.generate_default_avatar_url(agent.name)
            return AvatarResponse(avatar_url=default_avatar_url, avatar_type=AvatarType.DEFAULT.value)

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get avatar for agent {agent_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get agent avatar")


@avatar_router.post("/public/agent-avatars-by-version")
async def get_agent_avatars_by_version(
    request: BatchAgentAvatarRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
) -> BatchAgentAvatarResponse:
    """Batch fetch avatar info for a set of agent version IDs.

    Public endpoint that returns avatar_url/type and parent agent_id for each
    provided agent_version_id. If an agent has no custom avatar, a default
    avatar is generated for consistency.
    """
    # De-duplicate and bound the request size defensively
    version_ids = list(dict.fromkeys(request.agent_version_ids))[:200]

    agent_version_dao = AgentVersionDAO()
    agent_dao = AgentDAO()

    avatars: list[AgentAvatarInfo] = []

    for ver_id in version_ids:
        try:
            version = await agent_version_dao.get(db, ver_id)
            if not version:
                continue
            agent = await agent_dao.get(db, version.agent_id)
            if not agent:
                continue

            avatar_url = agent.avatar_url
            avatar_type = agent.avatar_type.value if agent.avatar_type else AvatarType.DEFAULT.value

            # Generate default avatar when missing
            if not avatar_url:
                avatar_url = avatar_service.generate_default_avatar_url(agent.name)
                avatar_type = AvatarType.DEFAULT.value

            avatars.append(
                AgentAvatarInfo(
                    agent_version_id=ver_id,
                    agent_id=agent.id,
                    avatar_url=avatar_url,
                    avatar_type=avatar_type,
                )
            )
        except Exception:
            # Do not fail the whole batch on individual errors
            logger.exception(f"Failed to resolve avatar for agent version {ver_id}")
            continue

    return BatchAgentAvatarResponse(avatars=avatars)
