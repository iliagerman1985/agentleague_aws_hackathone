"""Tool service for business logic operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import ToolId, UserId
from common.utils.utils import get_logger
from shared_db.crud.tool import ToolDAO
from shared_db.models.tool import ToolValidationStatus
from shared_db.schemas.tool import (
    ToolCreate,
    ToolResponse,
    ToolStatusResponse,
    ToolUpdate,
)
from shared_db.schemas.tool_usage import ToolUsageResponse

logger = get_logger()


class ToolService:
    """Service layer for tool operations.
    Handles business logic and coordinates between routers and DAOs.
    """

    def __init__(self, tool_dao: ToolDAO) -> None:
        """Initialize ToolService with ToolDAO dependency.

        Args:
            tool_dao: ToolDAO instance for database operations
        """
        self.tool_dao = tool_dao

    async def get_user_tools(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ToolResponse]:
        """Get all tools for a user.

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ToolResponse objects
        """
        logger.info(f"Getting tools for user {user_id}")
        return await self.tool_dao.get_by_user(db, user_id=user_id, skip=skip, limit=limit)

    async def get_user_tool_by_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolResponse | None:
        """Get a specific tool for a user.

        Args:
            db: Database session
            user_id: User ID
            tool_id: Tool ID

        Returns:
            ToolResponse if found and owned by user, None otherwise
        """
        logger.info(f"Getting tool {tool_id} for user {user_id}")
        return await self.tool_dao.get_by_user_and_id(db, user_id=user_id, tool_id=tool_id)

    async def create_tool(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_in: ToolCreate,
    ) -> ToolResponse:
        """Create a new tool for a user.

        Args:
            db: Database session
            user_id: User ID
            tool_in: Tool creation data

        Returns:
            Created ToolResponse
        """
        logger.info(f"Creating tool '{tool_in.display_name}' for user {user_id}")
        return await self.tool_dao.create(db, obj_in=tool_in, user_id=user_id)

    async def update_tool(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
        tool_in: ToolUpdate,
    ) -> ToolResponse | None:
        """Update a tool for a user.

        Args:
            db: Database session
            user_id: User ID
            tool_id: Tool ID
            tool_in: Tool update data

        Returns:
            Updated ToolResponse if found and owned by user, None otherwise
        """
        logger.info(f"Updating tool {tool_id} for user {user_id}")
        # Delegate update to DAO to avoid direct DB manipulation in service layer
        updated = await self.tool_dao.update_by_user_and_id(
            db,
            user_id=user_id,
            tool_id=tool_id,
            obj_in=tool_in,
        )
        if updated is None:
            logger.warning(f"Tool {tool_id} not found for user {user_id}")
        return updated

    async def get_tool_usage(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolUsageResponse:
        """Return agents (owned by user) that reference the given tool."""
        return await self.tool_dao.get_usage(db, user_id=user_id, tool_id=tool_id)

    async def get_tool_status(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolStatusResponse | None:
        """Get the validation status for a tool owned by the user."""
        return await self.tool_dao.get_status_by_user_and_id(db, user_id=user_id, tool_id=tool_id)

    async def set_tool_status(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
        validation_status: ToolValidationStatus,
    ) -> ToolStatusResponse | None:
        """Set the validation status for a tool owned by the user."""
        return await self.tool_dao.update_status_by_user_and_id(db, user_id=user_id, tool_id=tool_id, validation_status=validation_status)

    async def delete_tool(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
        detach_from_agents: bool = False,
    ) -> bool:
        """Delete a tool for a user.

        If detach_from_agents is True, remove references from the user's agents' versions
        before deletion to avoid FK violations.
        """
        logger.info(f"Deleting tool {tool_id} for user {user_id}; detach={detach_from_agents}")

        if detach_from_agents:
            # Delegate detachment to DAO layer
            _ = await self.tool_dao.detach_from_user_agents(db, user_id=user_id, tool_id=tool_id)

        return await self.tool_dao.delete_by_user_and_id(db, user_id=user_id, tool_id=tool_id)

    async def clone_tool(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        tool_id: ToolId,
    ) -> ToolResponse | None:
        """Clone a tool (typically a system tool) for a user.

        Creates a copy of the tool owned by the user.

        Args:
            db: Database session
            user_id: User ID
            tool_id: Tool ID to clone

        Returns:
            Cloned ToolResponse if successful, None if source tool not found
        """
        logger.info(f"Cloning tool {tool_id} for user {user_id}")
        return await self.tool_dao.clone_tool(db, tool_id=tool_id, user_id=user_id)

    async def get_tools_by_environment(
        self,
        db: AsyncSession,
        *,
        environment: str,
        user_id: UserId | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ToolResponse]:
        """Get tools for a specific environment with optional user filtering.

        Args:
            db: Database session
            environment: Game environment to filter tools by
            user_id: Optional user ID to include user's tools and system tools
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ToolResponse objects filtered by environment
        """
        logger.info(f"Getting tools for environment {environment}" + (f" and user {user_id}" if user_id else ""))
        return await self.tool_dao.get_by_environment(db, environment=environment, user_id=user_id, skip=skip, limit=limit)
