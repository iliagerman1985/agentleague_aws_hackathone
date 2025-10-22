"""Pydantic schemas for scoring system."""

from datetime import UTC, datetime

from game_api import GameType
from pydantic import Field

from common.ids import AgentId, AgentVersionId, GameId, PlayerId
from common.utils.json_model import JsonModel

# Import shared models to avoid duplication
from shared_db.models.agent import AgentGameRating, RecentGameEntry


class AgentProfileStats(JsonModel):
    """Overall statistics for an agent profile."""

    games_played: int = Field(default=0, description="Total games played")
    games_won: int = Field(default=0, description="Games won")
    games_lost: int = Field(default=0, description="Games lost")
    games_drawn: int = Field(default=0, description="Games drawn")
    win_rate: float = Field(default=0.0, description="Win rate percentage")
    recent_form: list[RecentGameEntry] = Field(default_factory=list, description="Recent game results")


class AgentProfileData(JsonModel):
    """Complete profile data for an agent."""

    agent_id: str = Field(description="Agent ID")
    name: str = Field(description="Agent name")
    description: str | None = Field(default=None, description="Agent description")
    game_environment: str = Field(description="Primary game environment")
    avatar_url: str | None = Field(default=None, description="Avatar URL")
    avatar_type: str = Field(description="Avatar type")
    is_system: bool = Field(default=False, description="Whether this is a system agent")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    username: str | None = Field(default=None, description="Username of the agent owner")

    overall_stats: AgentProfileStats = Field(description="Overall statistics")
    game_ratings: dict[str, AgentGameRating] = Field(default_factory=dict, description="Game-specific ratings")


class RatingUpdate(JsonModel):
    """Rating update information for a single agent."""

    agent_id: AgentId = Field(description="Agent ID")
    rating_change: float = Field(description="Rating change (positive or negative)")
    new_rating: float = Field(description="New rating after update")
    old_rating: float = Field(description="Previous rating before update")


class GameRatingUpdateRequest(JsonModel):
    """Request to update ratings after a game completes."""

    game_id: GameId = Field(description="ID of the completed game")
    game_type: GameType = Field(description="Type of game")
    player_ids: list[PlayerId] = Field(description="List of player IDs in the game")
    agent_mapping: dict[PlayerId, AgentId] = Field(description="Mapping from player IDs to agent IDs")
    agent_version_mapping: dict[AgentId, AgentVersionId] = Field(description="Mapping from agent IDs to agent version IDs")


class GameRatingUpdateResponse(JsonModel):
    """Response containing rating updates for all agents in a game."""

    game_id: GameId = Field(description="ID of the game")
    game_type: GameType = Field(description="Type of game")
    rating_updates: dict[AgentId, RatingUpdate] = Field(description="Rating updates for each agent")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When ratings were updated")
