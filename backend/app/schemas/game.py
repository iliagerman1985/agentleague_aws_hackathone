"""Game API schemas for request/response models."""

from enum import StrEnum
from typing import Any, Generic, TypeVar

from chess_game.chess_api import ChessPlaygroundOpponent, ChessSide, ChessState
from game_api import BaseGameConfig, BaseGameEvent, BaseGameState, GameType
from pydantic import Field, field_serializer
from texas_holdem.texas_holdem_api import TexasHoldemState

from common.ids import AgentVersionId, GameId, PlayerId
from common.utils.json_model import JsonModel
from shared_db.models.game import MatchmakingStatus


class UserGameResult(StrEnum):
    """User's result in a game."""

    WON = "won"
    LOST = "lost"
    DRAW = "draw"
    PLACED = "placed"  # For multi-player games where user didn't win but didn't lose all chips


TState = TypeVar("TState", bound=BaseGameState)
TConfig = TypeVar("TConfig", bound=BaseGameConfig)
TEvent = TypeVar("TEvent", bound=BaseGameEvent)


class PlayerInfo(JsonModel):
    """Player information"""

    id: PlayerId = Field(..., description="Player ID")
    agent_version_id: AgentVersionId = Field(..., description="Agent version ID")
    name: str = Field(..., description="Player/Agent name")
    username: str | None = Field(default=None, description="Unique username of the player who owns this agent (for matching)")
    display_name: str | None = Field(default=None, description="Display name of the player (nickname, full name, or username - for UI display)")
    rating: int | None = Field(default=None, description="Latest rating for the agent in this game type")
    color: ChessSide | None = Field(default=None, description="Player color/side for games with sides (e.g., ChessSide.WHITE or ChessSide.BLACK)")


class CreateGameRequest(JsonModel):
    """Request model for creating a new game."""

    game_type: GameType = Field(..., description="Type of game to create")
    config: dict[str, Any] = Field(..., description="Game configuration")
    agent_ids: list[AgentVersionId] = Field(..., description="List of agent IDs to participate in the game")


class CreatePlaygroundRequest(JsonModel):
    """Request model for creating a playground session."""

    agent_id: AgentVersionId = Field(..., description="Agent ID to use for all players in the playground")
    config: dict[str, Any] = Field(..., description="Game configuration")
    num_players: int = Field(default=3, description="Number of players in the playground (all using the same agent)")


class CreateChessPlaygroundRequest(JsonModel):
    """Request model for creating a chess playground session."""

    agent_id: AgentVersionId = Field(..., description="Agent ID to use when playing against the Stockfish bot")
    config: dict[str, Any] = Field(..., description="Game configuration")
    opponent: ChessPlaygroundOpponent = Field(
        default=ChessPlaygroundOpponent.BRAIN,
        description="Whether to face the Stockfish bot or play both sides manually",
    )
    user_side: ChessSide = Field(
        default=ChessSide.WHITE,
        description="Which side the user's agent plays (white or black)",
    )


class ExecuteTurnRequest(JsonModel):
    """Request model for executing a turn."""

    player_id: PlayerId = Field(..., description="ID of the player whose turn it is")
    turn: int = Field(..., description="Turn to execute, will be validated against the game state")
    move_override: Any | None = Field(default=None, description="Optional move override - if provided, this move will be used instead of calling the AI agent")


class FinalizeTimeoutRequest(JsonModel):
    """Request model for finalizing a game due to timeout."""

    player_id: PlayerId = Field(..., description="Player ID that allegedly timed out")


class GameStateResponse(JsonModel, Generic[TState, TConfig, TEvent]):
    """Response schema for game state.

    Generic over TState, TConfig, and TEvent to properly type fields based on game type.
    """

    id: GameId = Field(..., description="Game ID")
    game_type: GameType = Field(..., description="Type of game")
    state: TState = Field(..., description="Current game state")
    events: list[TEvent] = Field(..., description="Game events")
    config: TConfig = Field(..., description="Game configuration")
    version: int = Field(..., description="Game version for optimistic concurrency control")
    players: list[PlayerInfo] = Field(..., description="List of players with their IDs and names")
    is_playground: bool = Field(..., description="Whether this game is a playground")
    matchmaking_status: MatchmakingStatus | None = Field(default=None, description="Matchmaking status for non-playground games")

    @field_serializer("state", "config", when_used="json")
    def serialize_nested_models(self, value: Any) -> dict[str, Any]:
        """Serialize nested models using their actual runtime type, not the generic base type."""
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json", by_alias=True)
        return value

    @field_serializer("events", when_used="json")
    def serialize_events(self, value: list[Any]) -> list[dict[str, Any]]:
        """Serialize events using their actual runtime type."""
        return [event.model_dump(mode="json", by_alias=True) if hasattr(event, "model_dump") else event for event in value]


class TurnResultResponse(JsonModel, Generic[TState, TEvent]):
    """Response model for turn execution results.

    Generic over TState and TEvent to properly type fields based on game type.
    """

    game_id: GameId = Field(..., description="Game ID")
    new_state: TState = Field(..., description="Updated game state after turn")
    new_events: list[TEvent] = Field(..., description="New events generated during turn")
    is_finished: bool = Field(..., description="Whether the game is finished")
    current_player_id: PlayerId | None = Field(default=None, description="ID of the player whose turn it is next")
    new_coins_balance: int | None = Field(default=None, description="Updated coins balance after consuming tokens (for playground moves)")

    @field_serializer("new_state", when_used="json")
    def serialize_state(self, value: Any) -> dict[str, Any]:
        """Serialize state using its actual runtime type, not the generic base type."""
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json", by_alias=True)
        return value

    @field_serializer("new_events", when_used="json")
    def serialize_events(self, value: list[Any]) -> list[dict[str, Any]]:
        """Serialize events using their actual runtime type."""
        return [event.model_dump(mode="json", by_alias=True) if hasattr(event, "model_dump") else event for event in value]


class CreateGameResponse(JsonModel):
    """Response model for game creation."""

    game_id: GameId = Field(..., description="ID of the created game")
    message: str = Field(..., description="Success message")


# --- Playground creation (position-based) request models ---


class CreateFromDescriptionRequest(JsonModel):
    agent_id: AgentVersionId = Field(..., description="Agent to use when generating a state from description")
    llm_integration_id: str = Field(..., description="Selected LLM integration ID to use for generation")
    config: dict[str, Any] = Field(default_factory=dict, description="Game config override")
    num_players: int = Field(default=2, description="Number of players when applicable")


class ChessFromFENRequest(JsonModel):
    fen: str = Field(..., description="Starting FEN position")
    config: dict[str, Any] = Field(default_factory=dict, description="Game config override")
    opponent: ChessPlaygroundOpponent = Field(
        default=ChessPlaygroundOpponent.BRAIN,
        description="Opponent selection for the resulting playground",
    )
    agent_id: AgentVersionId | None = Field(
        default=None,
        description="Agent to use when playing against the Stockfish bot (ignored for self-play)",
    )
    user_side: ChessSide = Field(
        default=ChessSide.WHITE,
        description="Which side the user's agent plays (white or black)",
    )


class ChessFromMovesRequest(JsonModel):
    moves: str = Field(..., description="Move list in SAN/PGN-like format")
    config: dict[str, Any] = Field(default_factory=dict, description="Game config override")
    opponent: ChessPlaygroundOpponent = Field(
        default=ChessPlaygroundOpponent.BRAIN,
        description="Opponent selection for the resulting playground",
    )
    agent_id: AgentVersionId | None = Field(
        default=None,
        description="Agent to use when playing against the Stockfish bot (ignored for self-play)",
    )
    user_side: ChessSide = Field(
        default=ChessSide.WHITE,
        description="Which side the user's agent plays (white or black)",
    )


class ChessFromStateRequest(JsonModel):
    state_view: dict[str, Any] = Field(..., description="Validated chess state view JSON to start from")
    config: dict[str, Any] = Field(default_factory=dict, description="Game config override")
    opponent: ChessPlaygroundOpponent = Field(
        default=ChessPlaygroundOpponent.BRAIN,
        description="Opponent selection for the resulting playground",
    )
    agent_id: AgentVersionId | None = Field(
        default=None,
        description="Agent to use when playing against the Stockfish bot (ignored for self-play)",
    )
    user_side: ChessSide = Field(
        default=ChessSide.WHITE,
        description="Which side the user's agent plays (white or black)",
    )


class PokerFromStateRequest(JsonModel):
    agent_id: AgentVersionId = Field(..., description="Agent to use for all seats")
    state_view: dict[str, Any] = Field(..., description="Validated poker player-view JSON to start from")
    config: dict[str, Any] = Field(default_factory=dict, description="Game config override")
    num_players: int = Field(default=5, description="Number of players to allocate")


class GameConfigOptionsResponse(JsonModel):
    """Response model for game configuration options."""

    game_type: GameType = Field(..., description="Game type")
    default_config: BaseGameConfig = Field(..., description="Default configuration values")
    available_options: dict[str, Any] = Field(..., description="Available configuration options with metadata")


class GameConfigOptionsMapResponse(JsonModel):
    """Response containing configuration options for all game types."""

    config_options: dict[str, GameConfigOptionsResponse] = Field(..., description="Config options keyed by game type")


class ActiveGameResponse(JsonModel):
    """Response model for active games."""

    id: str = Field(..., description="Game ID")
    game_type: GameType = Field(..., description="Type of game")
    matchmaking_status: MatchmakingStatus = Field(..., description="Current matchmaking status")
    current_players: int = Field(..., description="Current number of players")
    max_players: int = Field(..., description="Maximum number of players allowed")
    min_players: int = Field(..., description="Minimum number of players required")
    created_at: str | None = Field(default=None, description="When the game was created (ISO string)")
    started_at: str | None = Field(default=None, description="When the game started (ISO string)")
    waiting_deadline: str | None = Field(default=None, description="Matchmaking deadline (ISO string)")
    time_remaining_seconds: int | None = Field(default=None, description="Seconds remaining until game starts (for waiting games)")
    allows_midgame_joining: bool = Field(..., description="Whether players can join after game starts")
    is_playground: bool = Field(..., description="Whether this is a practice game")
    # User's color (for chess) to display in lists/tables
    user_color: ChessSide | None = Field(default=None, description="User's color in this game (ChessSide.WHITE or ChessSide.BLACK when applicable)")
    user_agent_name: str | None = Field(default=None, description="Name of the user's agent in this game")


class GameHistoryResponse(JsonModel):
    """Response model for game history."""

    id: str = Field(..., description="Game ID")
    game_type: GameType = Field(..., description="Type of game")
    matchmaking_status: MatchmakingStatus = Field(..., description="Final matchmaking status")
    current_players: int = Field(..., description="Number of players in the game")
    max_players: int = Field(..., description="Maximum number of players allowed")
    created_at: str | None = Field(default=None, description="When the game was created (ISO string)")
    started_at: str | None = Field(default=None, description="When the game started (ISO string)")
    finished_at: str | None = Field(default=None, description="When the game finished (ISO string)")
    is_playground: bool = Field(..., description="Whether this was a practice game")
    has_events: bool = Field(..., description="Whether the game has recorded events for replay")
    final_state: ChessState | TexasHoldemState = Field(..., description="Final game state")
    # Game result fields
    winner_id: str | None = Field(default=None, description="Winner player ID (for Chess)")
    winners_ids: list[str] = Field(default_factory=list, description="Winner player IDs (for Texas Hold'em)")
    draw_reason: str | None = Field(default=None, description="Reason for draw (if applicable)")
    final_chip_counts: dict[str, int] | None = Field(default=None, description="Final chip counts (for Texas Hold'em)")
    user_result: UserGameResult | None = Field(default=None, description="User's result in this game")
    user_agent_name: str | None = Field(default=None, description="Name of the user's agent in this game")


class GameHistoryListResponse(JsonModel):
    """Response model for paginated game history."""

    games: list[GameHistoryResponse] = Field(..., description="List of completed games")
    total: int = Field(..., description="Total number of games")
    limit: int = Field(..., description="Number of games per page")
    offset: int = Field(..., description="Page offset")


class GameEventResponse(JsonModel):
    """Response model for game events."""

    id: str = Field(..., description="Event ID")
    type: str = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")
    created_at: str | None = Field(default=None, description="When the event was created (ISO string)")
    event_index: int = Field(..., description="Index of the event in the full chronological sequence (0-based)")


class GamesCountResponse(JsonModel):
    """Response model for user's games count."""

    count: int = Field(..., description="Number of games")
