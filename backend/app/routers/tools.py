"""Tool API routes for managing user tools."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_tool_service
from app.services.tool_service import ToolService
from common.ids import ToolId
from shared_db.schemas.tool import (
    ToolCreate,
    ToolResponse,
    ToolStatusResponse,
    ToolStatusUpdateRequest,
    ToolUpdate,
)
from shared_db.schemas.tool_usage import ToolUsageResponse
from shared_db.schemas.user import UserResponse

tools_router = APIRouter()


@tools_router.get("/tools")
async def get_user_tools(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
    skip: int = 0,
    limit: int = 100,
    environment: str | None = None,
) -> list[ToolResponse]:
    """Get all tools for the current user, optionally filtered by environment."""
    if environment:
        return await tool_service.get_tools_by_environment(db, environment=environment, user_id=current_user.id, skip=skip, limit=limit)
    return await tool_service.get_user_tools(db, user_id=current_user.id, skip=skip, limit=limit)


@tools_router.post("/tools", status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_in: ToolCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolResponse:
    """Create a new tool for the current user."""
    return await tool_service.create_tool(db, user_id=current_user.id, tool_in=tool_in)


@tools_router.get("/tools/{tool_id}")
async def get_tool(
    tool_id: ToolId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolResponse:
    """Get a specific tool for the current user."""
    tool = await tool_service.get_user_tool_by_id(db, user_id=current_user.id, tool_id=tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return tool


@tools_router.get("/tools/{tool_id}/usage")
async def get_tool_usage(
    tool_id: ToolId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolUsageResponse:
    """List agents that are using the specified tool (owned by current user)."""
    return await tool_service.get_tool_usage(db, user_id=current_user.id, tool_id=tool_id)


@tools_router.get("/tools/{tool_id}/validation-status")
async def get_tool_validation_status(
    tool_id: ToolId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolStatusResponse:
    """Get the validation status of a tool owned by the current user."""
    status_obj = await tool_service.get_tool_status(db, user_id=current_user.id, tool_id=tool_id)
    if not status_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return status_obj


@tools_router.put("/tools/{tool_id}/validation-status")
async def set_tool_validation_status(
    tool_id: ToolId,
    payload: ToolStatusUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolStatusResponse:
    """Set the validation status of a tool owned by the current user."""
    status_obj = await tool_service.set_tool_status(db, user_id=current_user.id, tool_id=tool_id, validation_status=payload.validation_status)
    if not status_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return status_obj


@tools_router.put("/tools/{tool_id}")
async def update_tool(
    tool_id: ToolId,
    tool_in: ToolUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolResponse:
    """Update a specific tool for the current user."""
    tool = await tool_service.update_tool(db, user_id=current_user.id, tool_id=tool_id, tool_in=tool_in)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return tool


@tools_router.post("/tools/{tool_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_tool(
    tool_id: ToolId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolResponse:
    """Clone a tool (typically a system tool) for the current user.

    Creates a copy of the tool owned by the current user.
    """
    cloned_tool = await tool_service.clone_tool(db, user_id=current_user.id, tool_id=tool_id)
    if not cloned_tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return cloned_tool


@tools_router.delete("/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: ToolId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    tool_service: Annotated[ToolService, Depends(get_tool_service)],
    detach_from_agents: bool = False,
) -> None:
    """Delete a specific tool for the current user.

    If detach_from_agents is True, also remove it from any of the user's agents that reference it.
    """
    success = await tool_service.delete_tool(db, user_id=current_user.id, tool_id=tool_id, detach_from_agents=detach_from_agents)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
