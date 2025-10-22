"""Game matching API schemas."""

from datetime import datetime
from typing import Any

from game_api import GameType
from pydantic import Field

from common.ids import AgentVersionId, GameId
from common.utils.json_model import JsonModel
from shared_db.models.game import MatchmakingStatus


class JoinMatchmakingRequest(JsonModel):
    """Request to join matchmaking for a game type."""

    game_type: GameType = Field(..., description="Type of game to join")
    agent_version_id: AgentVersionId = Field(..., description="Agent version to use")
    config: dict[str, Any] | None = Field(default=None, description="Game configuration overrides")


class JoinMatchmakingResponse(JsonModel):
    """Response after joining matchmaking."""

    game_id: GameId = Field(..., description="Game ID")
    matchmaking_status: MatchmakingStatus = Field(..., description="Matchmaking status")
    current_players: int = Field(..., description="Current number of players")
    min_players: int = Field(..., description="Minimum players needed")
    max_players: int = Field(..., description="Maximum players allowed")
    waiting_deadline: datetime | None = Field(..., description="When matchmaking will timeout")
    allows_midgame_joining: bool = Field(..., description="Whether mid-game joining is allowed")


class MatchmakingStatusResponse(JsonModel):
    """Current matchmaking status for a user."""

    game_id: GameId | None = Field(..., description="Current game ID if in matchmaking")
    game_type: GameType | None = Field(..., description="Game type if in matchmaking")
    matchmaking_status: MatchmakingStatus | None = Field(..., description="Matchmaking status")
    current_players: int = Field(..., description="Current players in game")
    min_players: int = Field(..., description="Minimum players needed")
    max_players: int = Field(..., description="Maximum players allowed")
    waiting_deadline: datetime | None = Field(..., description="When matchmaking will timeout")
    time_remaining_seconds: int | None = Field(..., description="Seconds remaining until timeout")


class LeaveMatchmakingRequest(JsonModel):
    """Request to leave matchmaking."""

    game_id: GameId = Field(..., description="Game ID to leave")


class LeaveMatchmakingResponse(JsonModel):
    """Response after leaving matchmaking."""

    message: str = Field(..., description="Status message")
    was_in_game: bool = Field(..., description="Whether user was actually in the game")
    game_ended: bool = Field(default=False, description="Whether the game ended as a result")
