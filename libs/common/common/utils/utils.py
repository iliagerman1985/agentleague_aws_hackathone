import asyncio
import sys
from collections.abc import Callable, Coroutine
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar, Token
from datetime import UTC, datetime, timedelta
from functools import wraps
from threading import Thread
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeGuard, TypeVar, cast

import structlog
from pydantic import BaseModel

T = TypeVar("T")
R_co = TypeVar("R_co", covariant=True)
K = TypeVar("K")
V = TypeVar("V")
P = ParamSpec("P")
TPydantic = TypeVar("TPydantic", bound=BaseModel)

if TYPE_CHECKING:
    ClassMethod = classmethod
else:
    ClassMethod = Callable[[Callable[Concatenate[T, P], R_co]], Callable[Concatenate[T, P], R_co]]


def is_dict(obj: Any) -> TypeGuard[dict[str, Any]]:
    return isinstance(obj, dict)


def is_list(obj: Any) -> TypeGuard[list[Any]]:
    return isinstance(obj, list)


def is_set(obj: Any) -> TypeGuard[set[Any]]:
    return isinstance(obj, set)


def get_now() -> datetime:
    return datetime.now(UTC)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    if name is None:
        # Get the name of the module that called this function
        frame = sys._getframe(1)  # type: ignore  # 0 would be get_logger, 1 is the caller
        module_name = frame.f_globals["__name__"].rsplit(".", 1)[-1]
        name = module_name
    return structlog.stdlib.get_logger(name)


def blocking_run_async[T](coro: Coroutine[Any, Any, T], timeout: int | None = None) -> T:
    try:
        return asyncio.run(coro)
    except RuntimeError:
        pass

    future: asyncio.Future[T] = asyncio.Future()

    def run() -> None:
        try:
            future.set_result(asyncio.run(coro))
        except Exception as e:
            future.set_exception(e)

    thread = Thread(target=run, name=f"blocking_run_async__{coro.__name__}", daemon=True)
    thread.start()
    thread.join(timeout)

    return future.result(timeout)  # type: ignore


class ContextVarManager(AbstractContextManager[T], AbstractAsyncContextManager[T]):
    """A convenience wrapper that is both a sync and async context manager.
    Use it when you have both sync and async contexts and want to reduce overall nesting.
    """

    _var: ContextVar[T]
    _value: T
    _token: Token[T] | None

    def __init__(self, var: ContextVar[T], value: T) -> None:
        self._var = var
        self._value = value
        self._token = None

    def __enter__(self) -> T:
        self._token = self._var.set(self._value)
        return self._value

    def __exit__(self, *exc_details: object) -> None:
        if self._token is not None:
            self._var.reset(self._token)

    async def __aenter__(self) -> T:
        return self.__enter__()

    async def __aexit__(self, *exc_details: object) -> None:
        self.__exit__(*exc_details)


def use_context_var(var: ContextVar[T], value: T) -> ContextVarManager[T]:
    return ContextVarManager(var, value)


def with_context_var(var: ContextVar[T], value_factory: Callable[[], T]) -> Callable[[Callable[P, R_co]], Callable[P, R_co]]:
    def decorator(func: Callable[P, R_co]) -> Callable[P, R_co]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R_co:
            token = var.set(value_factory())
            try:
                return func(*args, **kwargs)
            finally:
                var.reset(token)

        return cast("Callable[P, R_co]", wrapper)

    return decorator


def cached_classmethod[T, **P, R_co](func: Callable[Concatenate[T, P], R_co]) -> ClassMethod[T, P, R_co]:
    def wrapper(cls: T, *args: P.args, **kwargs: P.kwargs) -> R_co:
        if not hasattr(cls, "_cache"):
            setattr(cls, "_cache", {})
        cache = getattr(cls, "_cache")
        key = (func, args, frozenset(kwargs.items()))
        if key not in cache:
            cache[key] = func(cls, *args, **kwargs)
        return cache[key]

    return classmethod(wrapper)  # type: ignore


def pretty_print_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the string based on the duration
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts)


def human_readable_duration(duration_seconds: float) -> str:
    hours = int(duration_seconds // 3600)
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    milliseconds = int((duration_seconds % 1) * 1000)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    if milliseconds:
        parts.append(f"{milliseconds}ms")
    return " ".join(parts) if parts else "0s"


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary that will be updated
        update: Dictionary with values to update

    Returns:
        Updated dictionary with deeply merged values
    """
    merged = base.copy()

    for key, value in update.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], cast(dict[str, Any], value))
        else:
            merged[key] = value

    return merged


# fmt: off
latency_buckets_2m = [
    0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,  # 0.1 increments until 1
    1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0,  # 0.5 increments until 10
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,  # 1 increments until 30
    35, 40, 45, 50, 55, 60,  # 5 increments until 60
    70, 80, 90, 100, 110, 120,  # 10 increments until 120
]

latency_buckets_10s = [
    0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01,  # 1-10ms
    0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1,  # 15-100ms
    0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9,  # 125-900ms
    1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,  # 1-5s
    6.0, 7.0, 8.0, 9.0, 10.0,  # Extended range
]
# fmt: on
