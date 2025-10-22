from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, override

from sqlalchemy import event
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from common.core.lifecycle import Lifecycle
from common.utils import JsonSnakeCaseModel, decode_json, encode_json, get_logger, use_context_var

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger()


class DBConfig(JsonSnakeCaseModel):
    db_name: str
    user: str
    password: str
    host: str
    port: int
    driver: str = "postgresql+asyncpg"
    pool_size: int = 10
    pool_max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 300
    echo: bool = True
    echo_pool: bool = True
    pool_pre_ping: bool = False
    pool_use_lifo: bool = True
    pool_disabled: bool = False

    migrations_table: str = "alembic_version"

    @property
    def url(self) -> URL:
        return URL.create(self.driver, self.user, self.password, self.host, self.port, self.db_name)


class Db(Lifecycle):
    _config: DBConfig
    engine: AsyncEngine

    _session_context: ContextVar[AsyncSession]

    def __init__(self, config: DBConfig) -> None:
        super().__init__()
        self._config = config
        self._session_context = ContextVar("db_session")

        if config.driver == "postgresql+asyncpg":
            self.engine = create_async_engine(
                url=config.url,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=config.echo,
                echo_pool=config.echo_pool,
                max_overflow=config.pool_max_overflow,
                pool_size=config.pool_size,
                pool_timeout=config.pool_timeout,
                pool_recycle=config.pool_recycle,
                pool_pre_ping=config.pool_pre_ping,
                pool_use_lifo=config.pool_use_lifo,  # use lifo to reduce the number of idle connections
                poolclass=NullPool if config.pool_disabled else None,
            )
            """Database session factory.

                See [`async_sessionmaker()`][sqlalchemy.ext.asyncio.async_sessionmaker].
                """

            @event.listens_for(self.engine.sync_engine, "connect")
            def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:  # type: ignore
                """Using msgspec for serialization of the json column values means that the
                output is binary, not `str` like `json.dumps` would output.
                SQLAlchemy expects that the json serializer returns `str` and calls `.encode()` on the value to
                turn it to bytes before writing to the JSONB column. I'd need to either wrap `serialization.to_json` to
                return a `str` so that SQLAlchemy could then convert it to binary, or do the following, which
                changes the behavior of the dialect to expect a binary value from the serializer.
                See Also https://github.com/sqlalchemy/sqlalchemy/blob/14bfbadfdf9260a1c40f63b31641b27fe9de12a0/lib/sqlalchemy/dialects/postgresql/asyncpg.py#L934  pylint: disable=line-too-long
                """

                def encoder(bin_value: bytes) -> bytes:
                    return bin_value
                    # return b"\x01" + bin_value

                def decoder(bin_value: bytes) -> Any:
                    return decode_json(bin_value)

                    # the byte is the \x01 prefix for jsonb used by PostgreSQL.
                    # asyncpg returns it when format='binary'
                    # return decode_json(bin_value[1:])

                dbapi_connection.await_(
                    dbapi_connection.driver_connection.set_type_codec(
                        "jsonb",
                        encoder=encoder,
                        decoder=decoder,
                        schema="pg_catalog",
                        format="binary",
                    ),
                )
                dbapi_connection.await_(
                    dbapi_connection.driver_connection.set_type_codec(
                        "json",
                        encoder=encoder,
                        decoder=decoder,
                        schema="pg_catalog",
                        format="binary",
                    ),
                )
        elif config.driver == "sqlite+aiosqlite":
            self.engine = create_async_engine(
                url=config.url,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=config.echo,
                echo_pool=config.echo_pool,
                pool_recycle=config.pool_recycle,
                pool_pre_ping=config.pool_pre_ping,
            )
            """Database session factory.

                See [`async_sessionmaker()`][sqlalchemy.ext.asyncio.async_sessionmaker].
                """

            @event.listens_for(self.engine.sync_engine, "connect")
            def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:  # type: ignore
                """Override the default begin statement.  The disables the built in begin execution."""
                dbapi_connection.isolation_level = None

            @event.listens_for(self.engine.sync_engine, "begin")
            def _sqla_on_begin(dbapi_connection: Any) -> Any:  # type: ignore
                """Emits a custom begin"""
                dbapi_connection.exec_driver_sql("BEGIN")
        else:

            def json_serializer(bin_value: Any) -> str:
                return encode_json(bin_value).decode("utf-8")

            self.engine = create_async_engine(
                url=config.url,
                future=True,
                json_serializer=json_serializer,
                json_deserializer=decode_json,
                echo=config.echo,
                echo_pool=config.echo_pool,
                max_overflow=config.pool_max_overflow,
                pool_size=config.pool_size,
                pool_timeout=config.pool_timeout,
                pool_recycle=config.pool_recycle,
                pool_pre_ping=config.pool_pre_ping,
            )

    @property
    @override
    def _name_for_log(self) -> str:
        return f"Db[{self._config.db_name}]"

    @override
    async def _start(self) -> None:
        pass

    @override
    async def _stop(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def new_session(self) -> AsyncGenerator[AsyncSession]:
        async with (
            AsyncSession(self.engine, expire_on_commit=False, autoflush=False) as session,
            # session.begin(),
        ):
            yield session

    @asynccontextmanager
    async def context(self) -> AsyncGenerator[AsyncSession]:
        """Creates a session and stores it in the context var for the duration of the context."""
        async with self.new_session() as session, use_context_var(self._session_context, session):
            yield session

    def current_session(self) -> AsyncSession:
        return self._session_context.get()

    @asynccontextmanager
    async def use_current_session(self) -> AsyncGenerator[AsyncSession]:
        """Wraps the current session and commits it when exiting the context.
        Does not create a new session or transaction.
        """
        session = self.current_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
