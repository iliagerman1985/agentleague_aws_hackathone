from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_snake


class JsonModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    def to_json(self, by_alias: bool = True, pretty: bool = False) -> str:
        return self.model_dump_json(indent=2 if pretty else None, exclude_none=True, by_alias=by_alias)

    def to_dict(
        self,
        by_alias: bool | None = None,
        include: set[int] | set[str] | dict[int, Any] | dict[str, Any] | None = None,
        exclude: set[int] | set[str] | dict[int, Any] | dict[str, Any] | None = None,
        mode: Literal["json", "python", "human"] = "python",
    ) -> dict[str, Any]:
        return self.model_dump(
            exclude_none=True,
            by_alias=by_alias or (mode == "json"),
            include=include,
            exclude=exclude,
            mode=mode,
        )

    @property
    def is_empty(self) -> bool:
        return not any(
            value
            for field in self.__class__.model_fields
            if (value := getattr(self, field, None)) is not None and not (isinstance(value, JsonModel) and value.is_empty)
        )


class ImmutableJsonModel(JsonModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore", frozen=True)


class JsonSnakeCaseModel(JsonModel):
    model_config = ConfigDict(alias_generator=to_snake, populate_by_name=True, extra="ignore")


class JsonUpperSnakeCaseModel(JsonModel):
    model_config = ConfigDict(
        alias_generator=to_snake,
        str_to_upper=True,
        populate_by_name=True,
        extra="ignore",
    )


TJsonModel = TypeVar("TJsonModel", bound=JsonModel)
