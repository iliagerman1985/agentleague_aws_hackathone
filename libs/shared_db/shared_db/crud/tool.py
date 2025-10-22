"""Tool CRUD operations."""

import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import AgentVersionId, ToolId, UserId
from shared_db.models.agent import Agent, AgentVersion, AgentVersionTool
from shared_db.models.tool import Tool, ToolValidationStatus
from shared_db.schemas.tool import ToolCreate, ToolResponse, ToolStatusResponse, ToolUpdate
from shared_db.schemas.tool_usage import AgentSummary, ToolUsageResponse


def _to_machine_name(display_name: str) -> str:
    """Convert a human display name to a snake_case machine name.
    Only lowercase letters, digits, and underscores remain.
    """
    # Replace non-alphanumeric with underscores
    s = re.sub(r"[^A-Za-z0-9]+", "_", display_name)
    # Lowercase and strip extra underscores
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()


class ToolDAO:
    """Data Access Object for Tool operations.
    Returns Pydantic objects instead of SQLAlchemy models.
    """

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: ToolId) -> ToolResponse | None:
        """Get a tool by ID."""
        result = await db.execute(select(Tool).where(Tool.id == id))
        tool = result.scalar_one_or_none()
        return ToolResponse.model_validate(tool) if tool else None

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ToolResponse]:
        """Get multiple tools with pagination."""
        result = await db.execute(select(Tool).offset(skip).limit(limit))
        tools = result.scalars().all()
        return [ToolResponse.model_validate(tool) for tool in tools]

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ToolResponse]:
        """Get tools for a specific user with pagination, including system tools."""
        result = await db.execute(
            select(Tool).where((Tool.user_id == user_id) | (Tool.is_system == True)).order_by(Tool.updated_at.desc()).offset(skip).limit(limit)
        )
        tools = result.scalars().all()
        return [ToolResponse.model_validate(tool) for tool in tools]

    async def get_by_user_and_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolResponse | None:
        """Get a specific tool for a user, including system tools."""
        result = await db.execute(select(Tool).where(Tool.id == tool_id, (Tool.user_id == user_id) | (Tool.is_system == True)))
        tool = result.scalar_one_or_none()
        return ToolResponse.model_validate(tool) if tool else None

    async def get_by_ids(
        self,
        db: AsyncSession,
        tool_ids: list[ToolId],
    ) -> list[ToolResponse]:
        """Get multiple tools by their IDs in a single query."""
        if not tool_ids:
            return []

        result = await db.execute(select(Tool).where(Tool.id.in_(tool_ids)))
        tools = result.scalars().all()
        return [ToolResponse.model_validate(tool) for tool in tools]

    async def get_for_agent_version(self, db: AsyncSession, *, agent_version_id: AgentVersionId) -> list[ToolResponse]:
        """Get tools for a specific agent version ordered by execution order."""
        q = (
            select(Tool)
            .join(AgentVersionTool, Tool.id == AgentVersionTool.tool_id)
            .where(AgentVersionTool.agent_version_id == agent_version_id)
            .order_by(AgentVersionTool.order)
        )
        tools = (await db.execute(q)).scalars().all()
        return [ToolResponse.model_validate(t) for t in tools]

    async def get_by_environment(
        self,
        db: AsyncSession,
        *,
        environment: str,
        user_id: UserId | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ToolResponse]:
        """Get tools for a specific environment with optional user filtering."""
        query = select(Tool).where(Tool.environment == environment)

        if user_id is not None:
            query = query.where((Tool.user_id == user_id) | (Tool.is_system == True))

        query = query.order_by(Tool.updated_at.desc()).offset(skip).limit(limit)
        tools = (await db.execute(query)).scalars().all()
        return [ToolResponse.model_validate(tool) for tool in tools]

    async def create(self, db: AsyncSession, *, obj_in: ToolCreate, **kwargs: Any) -> ToolResponse:
        """Create a new tool for a user."""
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("user_id is required for tool creation")

        tool = Tool(
            user_id=user_id,
            display_name=obj_in.display_name,
            name=_to_machine_name(obj_in.display_name),
            description=obj_in.description,
            code=obj_in.code,
            environment=obj_in.environment,
            validation_status=ToolValidationStatus.VALID,  # All new tools are immediately valid
        )
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        return ToolResponse.model_validate(tool)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Tool,
        obj_in: ToolUpdate,
    ) -> ToolResponse:
        """Update an existing tool."""
        update_data = obj_in.model_dump(exclude_unset=True)
        # If display_name is provided, update both display_name and machine name
        if "display_name" in update_data and update_data["display_name"] is not None:
            db_obj.display_name = str(update_data["display_name"])
            db_obj.name = _to_machine_name(db_obj.display_name)
            update_data.pop("display_name", None)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return ToolResponse.model_validate(db_obj)

    async def update_by_user_and_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
        obj_in: ToolUpdate,
    ) -> ToolResponse | None:
        """Update a tool ensuring it belongs to the given user.

        System tools (is_system=True, user_id=None) cannot be updated.
        """
        result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.user_id == user_id))
        tool = result.scalar_one_or_none()
        if tool is None:
            return None
        # Prevent updating system tools
        if tool.is_system:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        # If display_name is provided, update both display_name and machine name
        if "display_name" in update_data and update_data["display_name"] is not None:
            tool.display_name = str(update_data["display_name"])
            tool.name = _to_machine_name(tool.display_name)
            update_data.pop("display_name", None)
        for field, value in update_data.items():
            setattr(tool, field, value)
        await db.commit()
        await db.refresh(tool)
        return ToolResponse.model_validate(tool)

    async def delete(self, db: AsyncSession, *, id: ToolId) -> bool:
        """Delete a tool by ID."""
        result = await db.execute(select(Tool).where(Tool.id == id))
        tool = result.scalar_one_or_none()
        if tool:
            await db.delete(tool)
            await db.commit()
            return True
        return False

    async def delete_by_user_and_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> bool:
        """Delete a specific tool for a user."""
        result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.user_id == user_id))
        tool = result.scalar_one_or_none()
        if tool:
            await db.delete(tool)
            await db.commit()
            return True
        return False

    async def get_usage(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolUsageResponse:
        """List agents (owned by user) that reference the given tool.

        Returns a ToolUsageResponse with AgentSummary items.
        """
        q = (
            select(Agent.id, Agent.name)
            .distinct()
            .join(AgentVersion, Agent.id == AgentVersion.agent_id)
            .join(AgentVersionTool, AgentVersion.id == AgentVersionTool.agent_version_id)
            .where(Agent.user_id == user_id, AgentVersionTool.tool_id == tool_id)
        )
        rows = (await db.execute(q)).all()
        agents = [AgentSummary(id=r[0], name=r[1]) for r in rows]
        return ToolUsageResponse(agents=agents, agents_count=len(agents))

    async def detach_from_user_agents(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> int:
        """Remove references of a tool from the user's agents' versions.

        Returns number of AgentVersionTool rows deleted.
        """
        ids_q = (
            select(AgentVersionTool.id)
            .join(AgentVersion, AgentVersionTool.agent_version_id == AgentVersion.id)
            .join(Agent, AgentVersion.agent_id == Agent.id)
            .where(Agent.user_id == user_id, AgentVersionTool.tool_id == tool_id)
        )
        avt_ids = [row[0] for row in (await db.execute(ids_q)).all()]
        if avt_ids:
            _ = await db.execute(delete(AgentVersionTool).where(AgentVersionTool.id.in_(avt_ids)))
            await db.commit()
        return len(avt_ids)

    async def get_status_by_user_and_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolStatusResponse | None:
        """Get validation status for a specific tool for a user.

        Returns ToolStatusResponse or None if not found.
        """
        result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.user_id == user_id))
        tool = result.scalar_one_or_none()
        if tool is None:
            return None
        return ToolStatusResponse(tool_id=tool.id, validation_status=tool.validation_status, updated_at=tool.updated_at)

    async def update_status_by_user_and_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
        validation_status: ToolValidationStatus,
    ) -> ToolStatusResponse | None:
        """Update validation status for a specific tool for a user.

        Returns ToolStatusResponse or None if not found/owned.
        """
        result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.user_id == user_id))
        tool = result.scalar_one_or_none()
        if tool is None:
            return None
        tool.validation_status = validation_status
        await db.commit()
        await db.refresh(tool)
        return ToolStatusResponse(tool_id=tool.id, validation_status=tool.validation_status, updated_at=tool.updated_at)

    async def clone_tool(
        self,
        db: AsyncSession,
        *,
        tool_id: ToolId,
        user_id: UserId,
    ) -> ToolResponse | None:
        """Clone a tool (typically a system tool) for a specific user.

        Creates a copy of the tool with the new user_id and is_system=False.
        The cloned tool will have " (Copy)" appended to its display name.

        Args:
            db: Database session
            tool_id: ID of the tool to clone
            user_id: ID of the user who will own the clone

        Returns:
            ToolResponse of the cloned tool, or None if source tool not found
        """
        # Get the source tool (can be system or user tool)
        result = await db.execute(select(Tool).where(Tool.id == tool_id))
        source_tool = result.scalar_one_or_none()
        if source_tool is None:
            return None

        # Create a new tool with copied data
        cloned_tool = Tool(
            user_id=user_id,
            display_name=f"{source_tool.display_name} (Copy)",
            name=_to_machine_name(f"{source_tool.display_name} (Copy)"),
            description=source_tool.description,
            code=source_tool.code,
            validation_status=source_tool.validation_status,
            is_system=False,  # Cloned tools are never system tools
        )
        db.add(cloned_tool)
        await db.commit()
        await db.refresh(cloned_tool)
        return ToolResponse.model_validate(cloned_tool)
