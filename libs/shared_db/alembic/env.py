import os
import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from alembic import context
from alembic.autogenerate import rewriter
from alembic.autogenerate.api import AutogenContext
from alembic.operations import ops
from alembic.runtime.environment import EnvironmentContext
from dotenv import load_dotenv
from sqlalchemy import Column, TypeDecorator, engine_from_config, pool

from common.core.config_service import ConfigService
from common.logging.setup_logging import setup_logging
from shared_db.db import Base

# Ensure models are imported so Base.metadata is populated for autogenerate
from shared_db.models import agent, game, llm_integration, tool, user  # type: ignore # noqa: F401

# Add the project root to sys.path to allow importing modules
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add the shared_db directory to sys.path
shared_db_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(shared_db_dir))

# Load .env file from the common directory
env_path = project_root / "libs" / "common" / ".env.development"
_ = load_dotenv(dotenv_path=env_path)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
use_alembic_logging = os.getenv("ALEMBIC_USE_DEFAULT_LOGGING", "false").lower() in {"true", "1", "t", "yes"}

if use_alembic_logging and config.config_file_name is not None:
    fileConfig(config.config_file_name)
else:
    setup_logging()

# add your model's MetaData object here
# for 'autogenerate' support

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Use config service to get database URL from secrets

config_service = ConfigService()
db_url = config_service.get_database_url()
if not db_url:
    raise ValueError("Database URL not found in configuration")

# Convert async database URL to sync URL for Alembic migrations
sync_db_url = db_url
if db_url.startswith("postgresql+asyncpg://"):
    sync_db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
elif db_url.startswith("sqlite+aiosqlite://"):
    sync_db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

# Prefer local secrets.yaml database URL if the file exists
try:
    local_secrets_path = project_root / "libs" / "common" / "secrets.yaml"
    if local_secrets_path.exists():
        with open(local_secrets_path, encoding="utf-8") as f:
            raw_local_secrets = yaml.safe_load(f) or {}
        database_config: dict[str, Any] | None = None
        if isinstance(raw_local_secrets, dict):
            secrets_dict = cast(dict[str, Any], raw_local_secrets)
            database_value = secrets_dict.get("database")
            if isinstance(database_value, dict):
                database_config = cast(dict[str, Any], database_value)
        local_url = database_config.get("url") if database_config is not None else None
        if isinstance(local_url, str) and local_url.strip():
            sync_db_url = local_url.strip()
except Exception:
    # Do not fail migrations if local secrets is unreadable; fall back to previous URL
    pass

config.set_main_option("sqlalchemy.url", sync_db_url)


writer = rewriter.Rewriter()


@writer.rewrites(ops.CreateTableOp)
def order_columns(
    context: EnvironmentContext,
    revision: tuple[str, ...],
    op: ops.CreateTableOp,
) -> ops.CreateTableOp:
    """Orders ID first and the audit columns immediately after."""
    special_names = {"id": -100, "created_at": -99, "updated_at": -98, "sa_orm_sentinel": 3001}
    cols_by_key: list[tuple[int, Column[Any]]] = [
        (
            special_names.get(col.key, index) if isinstance(col, Column) else 2000,
            col.copy(),  # type: ignore[attr-defined]
        )
        for index, col in enumerate(op.columns)
    ]
    columns = [col for _, col in sorted(cols_by_key, key=lambda entry: entry[0])]
    return ops.CreateTableOp(
        op.table_name,
        columns,
        schema=op.schema,
        # Remove when https://github.com/sqlalchemy/alembic/issues/1193 is fixed
        _namespace_metadata=op._namespace_metadata,  # type: ignore[attr-defined]
        **op.kw,
    )


def render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | Literal[False]:
    """Apply custom rendering for selected items."""
    from sqlalchemy import Enum

    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"

    # Handle Enum types to be database-agnostic
    if type_ == "type" and isinstance(obj, Enum):
        # Always render enums with native_enum=False for cross-database compatibility
        enum_class = obj.enum_class
        values = list(obj.enums) if getattr(obj, "enums", None) else []

        if not values and enum_class is not None:
            try:
                values = [member.value for member in enum_class]
            except Exception:  # pragma: no cover - defensive fallback
                if hasattr(enum_class, "__members__"):
                    values = list(enum_class.__members__.keys())

        if enum_class is not None:
            enum_name = obj.name or (enum_class.__name__.lower() if hasattr(enum_class, "__name__") else "enum")
        else:
            enum_name = obj.name or "enum"

        if not values:
            return False

        values_clause = ", ".join(repr(v) for v in values)
        return f"sa.Enum({values_clause}, name='{enum_name}', native_enum=False)"

    # default rendering for other objects
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    raise RuntimeError("Offline mode is not supported")

    # url = config.get_main_option("sqlalchemy.url")
    # context.configure(
    #     url=url,
    #     target_metadata=target_metadata,
    #     literal_binds=True,
    #     dialect_opts={"paramstyle": "named"},
    #     render_item=render_item,
    # )

    # with context.begin_transaction():
    #     context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
            process_revision_directives=writer,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
