"""Game models for game state management."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from game_api import GameType
from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.db_utils import DateTimeUTC, DbTSID
from common.ids import AgentVersionId, GameEventId, GameId, PlayerId, RequestId, UserId
from common.utils.tsid import TSID
from shared_db.db import Base
from shared_db.models.agent import AgentVersion
from shared_db.models.enum_utils import enum_values
from shared_db.models.user import User


class MatchmakingStatus(StrEnum):
    """Status of a game in the matchmaking system."""

    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class GamePlayer(Base):
    """Junction table for tracking user participation in games.

    This table tracks when users join and leave games through their agents,
    enabling efficient queries for active games by user and game type.
    """

    __tablename__ = "game_players"

    id: Mapped[PlayerId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)

    # Foreign keys
    game_id: Mapped[GameId] = mapped_column(DbTSID(), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    agent_version_id: Mapped[AgentVersionId] = mapped_column(DbTSID(), ForeignKey(AgentVersion.id), nullable=False)
    user_id: Mapped[UserId] = mapped_column(DbTSID(), ForeignKey(User.id), nullable=False)

    # Game environment type for efficient filtering
    env: Mapped[GameType] = mapped_column(
        Enum(GameType, native_enum=False, values_callable=enum_values),
        nullable=False,
    )

    # Timestamps
    join_time: Mapped[datetime] = mapped_column(DateTimeUTC(), nullable=False)
    leave_time: Mapped[datetime | None] = mapped_column(DateTimeUTC(), nullable=True)

    # Matchmaking fields
    is_system_player: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # Relationships
    game = relationship("Game", back_populates="game_players")
    agent_version = relationship(AgentVersion)
    user = relationship(User)

    # Indexes and constraints
    __table_args__ = (
        # Composite index for efficient queries of user's active games by environment
        Index("idx_game_players_user_env_leave", "user_id", "env", "leave_time"),
        # Index for efficient access control checks (is user in this game?)
        Index("idx_game_players_game_user", "game_id", "user_id"),
        # Unique constraint to ensure one agent version per game
        # UniqueConstraint("game_id", "agent_version_id", name="unique_game_agent_version"), # FIXME: Disabled until playground moves out of db
    )


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[GameEventId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    game_id: Mapped[GameId] = mapped_column(DbTSID(), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)

    type: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    game = relationship("Game", back_populates="events")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[GameId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)

    game_type: Mapped[GameType] = mapped_column(
        Enum(GameType, native_enum=False, values_callable=enum_values),
        nullable=False,
    )
    state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # User who requested/created the game (for LLM integration lookup)
    requesting_user_id: Mapped[UserId] = mapped_column(DbTSID(), ForeignKey(User.id), nullable=False, index=True)

    processing_started_at: Mapped[datetime | None] = mapped_column(DateTimeUTC(), nullable=True)
    processing_request_id: Mapped[RequestId | None] = mapped_column(DbTSID(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_playground: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    turn: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Matchmaking fields
    matchmaking_status: Mapped[MatchmakingStatus] = mapped_column(
        Enum(MatchmakingStatus, native_enum=False, values_callable=enum_values),
        default=MatchmakingStatus.WAITING,
        server_default=MatchmakingStatus.WAITING.value,
        nullable=False,
    )
    waiting_deadline: Mapped[datetime | None] = mapped_column(DateTimeUTC(), nullable=True)
    allows_midgame_joining: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    current_player_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    min_players_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_players_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTimeUTC(), nullable=True)

    game_players = relationship("GamePlayer", cascade="all, delete-orphan")
    events = relationship("GameEvent", back_populates="game", cascade="all, delete-orphan", order_by="GameEvent.id")
    requesting_user = relationship(User)
    llm_usage = relationship("LLMUsage", back_populates="game")
