from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable, Sequence
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from functools import partial
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path, PurePath
from re import Pattern
from typing import Any, Final, Literal, TypeVar, overload
from uuid import UUID

import msgspec

from common.utils.json_model import JsonModel
from common.utils.tsid import TSID

Serializer = Callable[[Any], Any]
TypeDecodersSequence = Sequence[tuple[Callable[[type], bool], Callable[[type, Any], Any]]] | None

type TypeEncodersMap = dict[Any, Callable[[Any], Any]]


class _EmptyEnum(Enum):
    """A sentinel enum used as placeholder."""

    EMPTY = 0


EmptyType = Literal[_EmptyEnum.EMPTY]
Empty: Final = _EmptyEnum.EMPTY


class SerializationError(Exception):
    """Encoding or decoding of an object failed."""


__all__ = (
    "decode_json",
    "decode_msgpack",
    "default_deserializer",
    "default_serializer",
    "encode_json",
    "encode_msgpack",
    "get_serializer",
)

T = TypeVar("T")

DEFAULT_TYPE_ENCODERS: TypeEncodersMap = {
    Path: str,
    PurePath: str,
    IPv4Address: str,
    IPv4Interface: str,
    IPv4Network: str,
    IPv6Address: str,
    IPv6Interface: str,
    IPv6Network: str,
    datetime: lambda val: val.isoformat(),
    date: lambda val: val.isoformat(),
    time: lambda val: val.isoformat(),
    deque: list,
    Decimal: lambda val: int(val) if val.as_tuple().exponent >= 0 else float(val),
    Pattern: lambda val: val.pattern,
    JsonModel: lambda val: val.to_dict(mode="json"),
    # TSID: lambda val: str(val.number),
    TSID: lambda val: val.to_string("s"),
}

# Support subclasses of stdlib types
DEFAULT_TYPE_ENCODERS.update(
    {
        str: str,
        int: int,
        float: float,
        set: set,
        frozenset: frozenset,
        bytes: bytes,
    },
)


def default_serializer(value: Any, type_encoders: TypeEncodersMap | None = None) -> Any:
    """Transform values non-natively supported by ``msgspec``

    Args:
        value: A value to serialize
        type_encoders: Mapping of types to callables to transform types
    Returns:
        A serialized value
    Raises:
        TypeError: if value is not supported
    """
    type_encoders = DEFAULT_TYPE_ENCODERS if type_encoders is None else {**DEFAULT_TYPE_ENCODERS, **type_encoders}

    # Handle SQLAlchemy models by converting them to dictionaries
    # Check if it's likely a SQLAlchemy model by looking for common attributes
    if hasattr(value, "__tablename__") and hasattr(value, "__table__"):
        return {c.name: default_serializer(getattr(value, c.name)) for c in value.__table__.columns}

    for base in value.__class__.__mro__[:-1]:
        try:
            encoder = type_encoders[base]
            return encoder(value)
        except KeyError:
            continue

    raise TypeError(f"Unsupported type: {type(value)!r}")


def default_deserializer(target_type: Any, value: Any, type_decoders: TypeDecodersSequence | None = None) -> Any:  # pragma: no cover
    """Transform values non-natively supported by ``msgspec``

    Args:
        target_type: Encountered type
        value: Value to coerce
        type_decoders: Optional sequence of type decoders

    Returns:
        A ``msgspec``-supported type
    """

    if isinstance(value, target_type):
        return value

    if type_decoders:
        for predicate, decoder in type_decoders:
            if predicate(target_type):
                return decoder(target_type, value)

    if issubclass(target_type, Path | PurePath | object | UUID):
        return target_type(value)  # type: ignore

    if target_type == TSID:
        return TSID.from_string_by_length(value)

    raise TypeError(f"Unsupported type: {type(value)!r}")


_default_json_encoder = msgspec.json.Encoder(enc_hook=default_serializer)
_default_json_decoder = msgspec.json.Decoder(dec_hook=default_deserializer)
_default_msgpack_encoder = msgspec.msgpack.Encoder(enc_hook=default_serializer)
_default_msgpack_decoder = msgspec.msgpack.Decoder(dec_hook=default_deserializer)


def encode_json(value: Any, serializer: Serializer | None = None) -> bytes:
    """Encode a value into JSON.

    Args:
        value: Value to encode
        serializer: Optional callable to support non-natively supported types.

    Returns:
        JSON as bytes

    Raises:
        SerializationException: If error encoding ``obj``.
    """
    try:
        return msgspec.json.encode(value, enc_hook=serializer) if serializer else _default_json_encoder.encode(value)
    except (TypeError, msgspec.EncodeError) as msgspec_error:
        raise SerializationError(str(msgspec_error)) from msgspec_error


def encode_json_str(value: Any, pretty: bool = False, serializer: Serializer | None = None) -> str:
    if pretty:
        return json.dumps(
            value,
            indent=2,
            check_circular=False,  # not needed, can't have a circular structure
            ensure_ascii=False,  # no need to escape unicode characters
        )
    return encode_json(value, serializer).decode("utf-8")


@overload
def decode_json(value: str | bytes, strict: bool = ...) -> Any: ...


@overload
def decode_json(value: str | bytes, type_decoders: TypeDecodersSequence | None, strict: bool = ...) -> Any: ...


@overload
def decode_json[T](value: str | bytes, target_type: type[T], strict: bool = ...) -> T: ...


@overload
def decode_json[T](value: str | bytes, target_type: type[T], type_decoders: TypeDecodersSequence | None, strict: bool = ...) -> T: ...


def decode_json[T](  # type: ignore[misc]
    value: str | bytes,
    target_type: type[T] | EmptyType = Empty,
    type_decoders: TypeDecodersSequence | None = None,
    strict: bool = True,
) -> T:
    """Decode a JSON string/bytes into an object.

    Args:
        value: Value to decode
        target_type: An optional type to decode the data into
        type_decoders: Optional sequence of type decoders
        strict: Whether type coercion rules should be strict. Setting to False enables
            a wider set of coercion rules from string to non-string types for all values

    Returns:
        An object

    Raises:
        SerializationException: If error decoding ``value``.
    """
    try:
        if target_type is Empty:
            return _default_json_decoder.decode(value)
        return msgspec.json.decode(
            value,
            dec_hook=partial(
                default_deserializer,
                type_decoders=type_decoders,
            ),
            type=target_type,
            strict=strict,
        )
    except msgspec.DecodeError as msgspec_error:
        raise SerializationError(str(msgspec_error)) from msgspec_error


def encode_msgpack(value: Any, serializer: Callable[[Any], Any] | None = default_serializer) -> bytes:
    """Encode a value into MessagePack.

    Args:
        value: Value to encode
        serializer: Optional callable to support non-natively supported types

    Returns:
        MessagePack as bytes

    Raises:
        SerializationException: If error encoding ``obj``.
    """
    try:
        if serializer is None or serializer is default_serializer:
            return _default_msgpack_encoder.encode(value)
        return msgspec.msgpack.encode(value, enc_hook=serializer)
    except (TypeError, msgspec.EncodeError) as msgspec_error:
        raise SerializationError(str(msgspec_error)) from msgspec_error


@overload
def decode_msgpack(value: bytes, strict: bool = ...) -> Any: ...


@overload
def decode_msgpack(value: bytes, type_decoders: TypeDecodersSequence | None, strict: bool = ...) -> Any: ...


@overload
def decode_msgpack[T](value: bytes, target_type: type[T], strict: bool = ...) -> T: ...


@overload
def decode_msgpack[T](value: bytes, target_type: type[T], type_decoders: TypeDecodersSequence | None, strict: bool = ...) -> T: ...


def decode_msgpack[T](  # type: ignore[misc]
    value: bytes,
    target_type: type[T] | EmptyType = Empty,
    type_decoders: TypeDecodersSequence | None = None,
    strict: bool = True,
) -> T:
    """Decode a MessagePack string/bytes into an object.

    Args:
        value: Value to decode
        target_type: An optional type to decode the data into
        type_decoders: Optional sequence of type decoders
        strict: Whether type coercion rules should be strict. Setting to False enables
            a wider set of coercion rules from string to non-string types for all values

    Returns:
        An object

    Raises:
        SerializationException: If error decoding ``value``.
    """
    try:
        if target_type is Empty:
            return _default_msgpack_decoder.decode(value)
        return msgspec.msgpack.decode(
            value,
            dec_hook=partial(default_deserializer, type_decoders=type_decoders),
            type=target_type,
            strict=strict,
        )
    except msgspec.DecodeError as msgspec_error:
        raise SerializationError(str(msgspec_error)) from msgspec_error


def get_serializer(type_encoders: TypeEncodersMap | None = None) -> Serializer:
    """Get the serializer for the given type encoders."""

    if type_encoders:
        return partial(default_serializer, type_encoders=type_encoders)

    return default_serializer


class BaseStruct(msgspec.Struct):
    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__struct_fields__ if getattr(self, f, None) != msgspec.UNSET}


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Camelized Base Struct"""


class Message(CamelizedBaseStruct):
    message: str
