"""Custom SQLAlchemy column type for Pydantic models.

This module provides a custom column type that automatically serializes and deserializes
Pydantic models to/from JSON in the database, ensuring proper camelCase conversion.
"""

from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel, TypeAdapter
from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

T = TypeVar("T", bound=BaseModel)


class PydanticType(TypeDecorator[T], Generic[T]):
    """SQLAlchemy column type that stores Pydantic models as JSON.

    This type automatically:
    - Serializes Pydantic models to JSON (with camelCase) when saving to database
    - Deserializes JSON back to Pydantic models when loading from database
    - Handles discriminated unions using TypeAdapter

    Usage:
        class MyModel(Base):
            state: Mapped[ChessState] = mapped_column(PydanticType(ChessState))
            config: Mapped[ChessConfig] = mapped_column(PydanticType(ChessConfig))
            # For discriminated unions:
            event: Mapped[ChessEvent] = mapped_column(PydanticType(ChessEvent))
    """

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_type: type[BaseModel] | Any, *args: Any, **kwargs: Any) -> None:
        """Initialize the PydanticType.
        
        Args:
            pydantic_type: The Pydantic model class or union type to use for serialization/deserialization
        """
        super().__init__(*args, **kwargs)
        self.pydantic_type = pydantic_type
        # Use TypeAdapter to handle both regular models and discriminated unions
        self.type_adapter = TypeAdapter(pydantic_type)

    def process_bind_param(self, value: T | None, dialect: Any) -> Any:
        """Convert Pydantic model to dict for database storage.

        Args:
            value: Pydantic model instance
            dialect: SQLAlchemy dialect (unused but required by interface)

        Returns:
            Dictionary representation with camelCase keys (via by_alias=True)
        """
        if value is None:
            return None

        # Serialize with aliases (camelCase) for storage
        # Note: We store as camelCase in the database for consistency with API responses
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value: Any, dialect: Any) -> T | None:
        """Convert dict from database to Pydantic model.

        Args:
            value: JSON-compatible value from database (typically dict, but could be other JSON types)
            dialect: SQLAlchemy dialect (unused but required by interface)

        Returns:
            Pydantic model instance
        """
        if value is None:
            return None

        # Deserialize using TypeAdapter (handles both regular models and discriminated unions)
        return cast(T, self.type_adapter.validate_python(value))

