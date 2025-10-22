"""Tool creation agent API routes."""

import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_tool_creation_agent_service
from app.schemas.tool_creation_agent import (
    ToolAgentChatRequest,
    ToolAgentChatResponse,
    ToolAgentStreamChunk,
)
from app.services.tool_creation_agent_service import ToolCreationAgentService
from common.core.app_error import AppException
from common.core.logging_service import get_logger
from shared_db.schemas.user import UserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/tool-agent", tags=["Tool Creation Agent"])


async def _stream_response_as_json(
    service: ToolCreationAgentService,
    db: AsyncSession,
    request: ToolAgentChatRequest,
) -> AsyncGenerator[str]:
    """Convert agent stream chunks to JSON for HTTP response."""
    try:
        async for chunk in service.stream_chat(
            db=db,
            message=request.message,
            conversation_history=request.conversation_history,
            integration_id=request.integration_id,
            environment=request.environment,
            model_id=request.model_id,
            current_tool_code=request.current_tool_code,
        ):
            # Handle code_artifact from service chunk
            tool_artifact = None
            if chunk.get("code_artifact"):
                from common.agents.models import CodeArtifact

                tool_artifact = CodeArtifact(**chunk["code_artifact"])

            # Determine the chunk type based on what's present
            # Frontend expects "tool" type when code is generated, "test" when test JSON is present
            chunk_type = chunk.get("type", "content")
            has_tool = tool_artifact is not None
            has_test_json = chunk.get("test_json") is not None

            if chunk_type == "done":
                # If we have both tool and test JSON, send two separate chunks
                if has_tool and has_test_json:
                    # First, send the tool chunk
                    tool_chunk = ToolAgentStreamChunk(
                        type="tool",
                        content=chunk.get("content"),
                        tool_artifact=tool_artifact,
                        test_artifact=None,
                        is_complete=False,  # Not complete yet - test chunk coming
                        should_summarize=chunk.get("should_summarize", False),
                        error=chunk.get("error"),
                    )
                    tool_dict = tool_chunk.model_dump()
                    if chunk.get("description"):
                        tool_dict["description"] = chunk["description"]
                    yield json.dumps(tool_dict) + "\n"

                    # Then, send the test chunk
                    test_chunk = ToolAgentStreamChunk(
                        type="test",
                        content=None,
                        tool_artifact=None,
                        test_artifact=None,
                        is_complete=chunk.get("is_complete", False),
                        should_summarize=False,
                        error=None,
                    )
                    test_dict = test_chunk.model_dump()
                    test_dict["test_json"] = chunk["test_json"]
                    yield json.dumps(test_dict) + "\n"
                    continue  # Skip the normal chunk sending below

                # If only tool, change type to "tool"
                elif has_tool:
                    chunk_type = "tool"
                # If only test JSON, change type to "test"
                elif has_test_json:
                    chunk_type = "test"

            # Convert chunk to ToolAgentStreamChunk
            stream_chunk = ToolAgentStreamChunk(
                type=chunk_type,
                content=chunk.get("content"),
                tool_artifact=tool_artifact,
                test_artifact=None,  # Not used - test_json is in the chunk directly
                is_complete=chunk.get("is_complete", False),
                should_summarize=chunk.get("should_summarize", False),
                error=chunk.get("error"),
            )

            # Add test_json and description to the output if present
            chunk_dict = stream_chunk.model_dump()
            if chunk.get("test_json"):
                chunk_dict["test_json"] = chunk["test_json"]
            if chunk.get("description"):
                chunk_dict["description"] = chunk["description"]

            yield json.dumps(chunk_dict) + "\n"

    except AppException as e:
        # Handle AppException (including guardrail violations) with detailed message
        logger.warning(f"AppException in agent stream: {e.details.message}")
        error_chunk = ToolAgentStreamChunk(
            type="error",
            error=e.details.message,
            is_complete=True,
        )
        yield json.dumps(error_chunk.model_dump()) + "\n"
    except Exception as e:
        logger.exception("Error in agent stream")
        error_chunk = ToolAgentStreamChunk(
            type="error",
            error=str(e),
            is_complete=True,
        )
        yield json.dumps(error_chunk.model_dump()) + "\n"


@router.post("/chat/stream")
async def stream_tool_agent_chat(
    request: ToolAgentChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ToolCreationAgentService, Depends(get_tool_creation_agent_service)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream conversation with tool creation agent.

    The agent is environment-agnostic and does NOT interact with the database.
    It only generates and validates code.
    """
    try:
        logger.info(f"Starting tool agent stream for environment {request.environment.value}")

        return StreamingResponse(
            _stream_response_as_json(
                service=service,
                db=db,
                request=request,
            ),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.exception("Error starting tool agent stream")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start tool agent stream: {e!s}",
        ) from e


@router.post("/chat")
async def tool_agent_chat(
    request: ToolAgentChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[ToolCreationAgentService, Depends(get_tool_creation_agent_service)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> ToolAgentChatResponse:
    """Non-streaming conversation with tool creation agent.

    The agent is environment-agnostic and does NOT interact with the database.
    It only generates and validates code.
    """
    try:
        logger.info(f"Starting tool agent chat for environment {request.environment.value}")

        # Get agent response
        response = await service.chat(
            db=db,
            message=request.message,
            conversation_history=request.conversation_history,
            integration_id=request.integration_id,
            environment=request.environment,
            model_id=request.model_id,
            current_tool_code=request.current_tool_code,
        )

        return ToolAgentChatResponse(
            content=response.content,
            code_artifact=response.code_artifact,
            test_artifact=response.test_artifact,
            model_used=response.model_used,
            should_summarize=response.should_summarize,
        )

    except AppException as e:
        # Handle AppException (including guardrail violations) with detailed message
        logger.warning(f"AppException in tool agent chat: {e.details.message}")
        raise HTTPException(
            status_code=e.http_status or status.HTTP_400_BAD_REQUEST,
            detail=e.details.message,
        ) from e
    except ValueError as e:
        logger.warning(f"Validation error in tool agent chat: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Error in tool agent chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process tool agent chat: {e!s}",
        ) from e
