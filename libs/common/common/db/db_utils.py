from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from msgspec import Struct
from pydantic import AnyHttpUrl, AnyUrl, EmailStr, Json
from sqlalchemy import JSON, BigInteger, Date, DateTime, Dialect, MetaData, String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import registry
from sqlalchemy.types import JSON as _JSON

from common.utils.json_model import JsonModel
from common.utils.tsid import TSID

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect
    from sqlalchemy.sql.schema import _NamingSchemaParameter as NamingSchemaParameter  # pyright: ignore[reportPrivateUsage]
    from sqlalchemy.types import TypeEngine

convention: NamingSchemaParameter = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def create_registry(custom_annotation_map: dict[Any, type[TypeEngine[Any]] | TypeEngine[Any]] | None = None) -> registry:
    """Create a new SQLAlchemy registry."""

    meta = MetaData(naming_convention=convention)
    type_annotation_map: dict[Any, type[TypeEngine[Any]] | TypeEngine[Any]] = {
        datetime: DateTimeUTC,
        date: Date,
        dict: JsonB,
        EmailStr: String,
        AnyUrl: String,
        AnyHttpUrl: String,
        Json: JsonB,
        Struct: JsonB,
    }
    if custom_annotation_map is not None:
        type_annotation_map.update(custom_annotation_map)
    return registry(metadata=meta, type_annotation_map=type_annotation_map)


JsonB = _JSON().with_variant(PG_JSONB, "postgresql").with_variant(PG_JSONB, "cockroachdb")
"""A JSON type that uses  native ``JSONB`` where possible and ``Binary`` or ``Blob`` as
an alternative.
"""


class PydanticJson[TJsonModel: JsonModel](TypeDecorator[TJsonModel | None]):
    impl = JSON  # Store the data as JSON in the database
    cache_ok = True

    _deserialize: Callable[[dict[str, Any]], TJsonModel | None]

    def __init__(self, deserialize: Callable[[dict[str, Any]], TJsonModel | None], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._deserialize = deserialize

    def process_bind_param(self, value: TJsonModel | None, dialect: Dialect) -> dict[str, Any] | None:
        if value is None:
            return None
        return value.to_dict(mode="json")

    def process_result_value(self, value: dict[str, Any] | None, dialect: Dialect) -> TJsonModel | None:
        if value is None:
            return None
        return self._deserialize(value)


class DbTSID(TypeDecorator[TSID]):
    impl = BigInteger
    cache_ok = True

    def process_bind_param(self, value: TSID | int | str | None, dialect: Dialect) -> int | None:
        match value:
            case TSID():
                return value.number
            case int():
                return value
            case str():
                return TSID.from_string_by_length(value).number
            case None:
                return None
            case _:
                raise ValueError(f"Invalid value for DbTSID: {value}")

    def process_result_value(self, value: TSID | int | str | None, dialect: Dialect) -> TSID | None:
        match value:
            case int():
                return TSID(value)
            case TSID():
                return value
            case str():
                return TSID.from_string_by_length(value)
            case None:
                return None
            case _:
                raise ValueError(f"Invalid value for DbTSID: {value}")


class DateTimeUTC(TypeDecorator[datetime]):
    """Timezone Aware DateTime.

    Ensure UTC is stored in the database and that TZ aware dates are returned for all dialects.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    @property
    def python_type(self) -> type[datetime]:
        return datetime

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return value
        if not value.tzinfo:
            msg = "tzinfo is required"
            raise TypeError(msg)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


@asynccontextmanager
async def use_session(session: AsyncSession) -> AsyncGenerator[AsyncSession]:
    """Commits the session when exiting the context."""
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
