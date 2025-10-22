"""Utilities for working with SQLAlchemy enums backed by StrEnum values."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

EnumT = TypeVar("EnumT", bound=Enum)


def enum_values(enum_cls: type[EnumT]) -> list[Any]:
    """Return the concrete values for a Python ``Enum`` class.

    SQLAlchemy's ``Enum`` type calls ``values_callable`` with the enum class to
    obtain the set of values to persist. Our enums inherit from ``StrEnum`` and
    store lowercase strings, so we must surface the ``.value`` attributes rather
    than the member names to keep database defaults consistent.
    """
    return [member.value for member in enum_cls]
