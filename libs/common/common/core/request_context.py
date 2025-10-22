from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextvars import ContextVar, Token
from functools import wraps
from typing import Any

from pydantic import Field

from common.ids import AgentVersionId, RequestId, UserId
from common.utils import ContextVarManager, JsonModel, get_logger, use_context_var
from common.utils.tsid import TSID

logger = get_logger()


class RequestContext(JsonModel):
    request_id: RequestId = Field(default_factory=lambda: RequestId(TSID.create()))
    endpoint: str | None = None
    trigger: str | None = None

    user_id: UserId | None = None

    agent_version_id: AgentVersionId | None = None

    experiments: dict[str, Any] | None = None

    @property
    def user_id_or_throw(self) -> UserId:
        return self._get_field("user_id")

    @property
    def agent_version_id_or_throw(self) -> AgentVersionId:
        return self._get_field("agent_version_id")

    def _get_field(self, name: str) -> Any:
        value = getattr(self, name, None)
        if value is None:
            raise Exception(f"No '{name}' in request context!")
        return value

    def fallback_from(self, fallback: RequestContext) -> None:
        for key in fallback.model_fields_set:
            value = getattr(self, key, None)
            if value is None:
                fallback_value = getattr(fallback, key, None)
                if fallback_value is not None:
                    setattr(self, key, fallback_value)

    def override_from(self, override: RequestContext) -> None:
        for key in override.model_fields_set:
            value = getattr(override, key, None)
            if value is not None:
                setattr(self, key, value)

    @staticmethod
    def default() -> RequestContext:
        return RequestContext()

    @staticmethod
    def deserialize_safe(data: dict[str, Any] | None) -> RequestContext:
        if not data:
            return RequestContext.default()
        try:
            return RequestContext.model_validate(data)
        except Exception as e:
            logger.exception("Invalid request context", exc_info=e)
            return RequestContext(
                request_id=data.get("request_id") or RequestId(TSID.create()),
                trigger=data.get("trigger"),
                user_id=data.get("user_id"),
                agent_version_id=data.get("agent_version_id"),
                experiments=data.get("experiments", {}),
            )

    @staticmethod
    def get() -> RequestContext:
        return _context_var.get()

    @staticmethod
    def get_or_none() -> RequestContext | None:
        return _context_var.get(None)

    @staticmethod
    def set(request_context: RequestContext) -> Token[RequestContext]:
        return _context_var.set(request_context)

    @staticmethod
    def reset(token: Token[RequestContext]) -> None:
        _context_var.reset(token)

    @staticmethod
    def context() -> ContextVarManager[RequestContext]:
        return use_context_var(_context_var, _context())

    @staticmethod
    def with_request_context() -> Callable[[Any], Any]:
        return RequestContext.wrap_with_context

    @staticmethod
    def wrap_with_context(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with RequestContext.context():
                    return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with RequestContext.context():
                return func(*args, **kwargs)

        return sync_wrapper

    @classmethod
    def install(cls: type[RequestContext]) -> None:
        """Should only be called if the service has a custom RequestContext (subtype)"""

        global _context
        _context = cls


_context: type[RequestContext] = RequestContext
_context_var: ContextVar[RequestContext] = ContextVar("request_context")
