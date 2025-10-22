from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Generic, Literal, Protocol, TypeVar

from pydantic import Field

from common.ids import AgentVersionId, EventId, GameId, PlayerId
from common.types import AgentReasoning, ExecutedToolCall
from common.utils import TSID, JsonModel
from common.utils.utils import get_now

NO_PLAYER_ID = PlayerId(TSID(0))


# ----- UI Config Option Models -----
class EnumOption(JsonModel):
    value: str | int | bool
    label: str
    default: bool | None = None


class GameConfigOption(JsonModel):
    type: Literal["enum", "number", "boolean", "string"]
    options: list[EnumOption] | None = None
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None
    default: Any | None = None
    label: str | None = None


class GameResult(JsonModel):
    """Game result information extracted from final state.

    This provides a standardized way to extract game outcome information
    across different game types.
    """

    winner_id: PlayerId | None = Field(default=None, description="Single winner player ID (for 1v1 games like Chess)")
    winners_ids: list[PlayerId] = Field(default_factory=list, description="Multiple winner player IDs (for multi-player games)")
    draw_reason: str | None = Field(default=None, description="Reason for draw (if applicable)")
    final_scores: dict[PlayerId, int] | None = Field(default=None, description="Final scores/chips for each player (if applicable)")


class GameScoring(JsonModel, ABC):
    """Abstract base class for game-specific scoring systems.

    Provides a standardized interface for calculating scores, ratings,
    and performance metrics across different game types.
    """

    @classmethod
    @abstractmethod
    def calculate_player_score(cls, result: GameResult, player_id: PlayerId, opponent_ratings: dict[PlayerId, float]) -> float:
        """Calculate the score for a player based on game result.

        Args:
            result: The game result containing winner/loser information
            player_id: The player ID to calculate score for
            opponent_ratings: Dictionary mapping opponent IDs to their current ratings

        Returns:
            Numeric score for the player (higher is better)
        """
        ...

    @classmethod
    @abstractmethod
    def calculate_rating_change(cls, player_rating: float, opponent_rating: float, actual_score: float, k_factor: float = 32.0) -> float:
        """Calculate rating change using game-specific algorithm.

        Args:
            player_rating: Current rating of the player
            opponent_rating: Current rating of the opponent
            actual_score: Actual score achieved (1.0 for win, 0.5 for draw, 0.0 for loss)
            k_factor: K-factor for rating calculation (default 32)

        Returns:
            Rating change (positive for gain, negative for loss)
        """
        ...

    @classmethod
    @abstractmethod
    def update_rating(cls, current_rating: float, rating_change: float) -> float:
        """Update a player's rating, ensuring it doesn't go below minimum.

        Args:
            current_rating: Current rating
            rating_change: Rating change (positive or negative)

        Returns:
            New rating (with minimum enforced)
        """
        ...

    @classmethod
    @abstractmethod
    def get_default_rating(cls) -> float:
        """Get the default starting rating for new players.

        Returns:
            Default rating value
        """
        ...

    @classmethod
    def calculate_rating_update(
        cls, result: GameResult, player_id: PlayerId, current_rating: float, games_played: int, opponent_ratings: dict[PlayerId, float]
    ) -> tuple[float, float]:
        """Calculate rating change for a player based on game result.

        This is the main entry point for rating calculations. Each game type
        implements its own logic for determining win/loss/draw and calculating
        rating changes.

        Args:
            result: The game result
            player_id: The player to calculate rating for
            current_rating: Player's current rating
            games_played: Number of games the player has played
            opponent_ratings: Dictionary mapping opponent IDs to their ratings

        Returns:
            Tuple of (rating_change, new_rating)
        """
        # Default implementation: simple Elo-style calculation
        # Determine actual score
        if result.winner_id == player_id or player_id in result.winners_ids:
            actual_score = 1.0  # Win
        elif result.draw_reason is not None:
            actual_score = 0.5  # Draw
        else:
            actual_score = 0.0  # Loss

        # Calculate average opponent rating
        if opponent_ratings:
            avg_opponent_rating = sum(opponent_ratings.values()) / len(opponent_ratings)
        else:
            avg_opponent_rating = cls.get_default_rating()

        # Get K-factor (can be overridden by subclasses)
        k_factor = cls.get_k_factor(games_played, current_rating)

        # Calculate rating change
        rating_change = cls.calculate_rating_change(current_rating, avg_opponent_rating, actual_score, k_factor)

        # Update rating
        new_rating = cls.update_rating(current_rating, rating_change)

        return rating_change, new_rating

    @classmethod
    def get_k_factor(cls, games_played: int, current_rating: float) -> int:
        """Get K-factor for rating calculations.

        Default implementation returns a fixed K-factor of 32.
        Games can override this to provide dynamic K-factors based on experience/rating.

        Args:
            games_played: Number of games the player has played
            current_rating: Current rating of the player

        Returns:
            K-factor value for rating calculations
        """
        return 32

    @classmethod
    @abstractmethod
    def get_score_metrics(cls, result: GameResult, player_id: PlayerId) -> dict[str, Any]:
        """Get game-specific performance metrics for a player.

        Args:
            result: The game result
            player_id: The player ID to get metrics for

        Returns:
            Dictionary of performance metrics specific to the game type
        """
        ...

    @classmethod
    @abstractmethod
    def get_result_description(cls, result: GameResult, player_id: PlayerId) -> str:
        """Get human-readable description of the result for a player.

        Args:
            result: The game result
            player_id: The player ID to describe result for

        Returns:
            Human-readable result description
        """
        ...


class GameType(StrEnum):
    """Supported game types."""

    TEXAS_HOLDEM = "texas_holdem"
    CHESS = "chess"


class FinishDecision(StrEnum):
    """Decision on whether to finish the game after a player leaves."""

    CONTINUE = "continue"  # Game continues with remaining players
    FINISH = "finish"  # Game should be finished (below minimum players)
    CANCEL = "cancel"  # Game should be cancelled (no players left)


class BaseGameConfig(JsonModel, ABC):
    """Base configuration for all games."""

    env: GameType = Field(..., description="Type of game")
    max_players: int = Field(..., description="Maximum number of players", ge=2)
    min_players: int = Field(..., description="Minimum number of players", ge=2)

    def model_post_init(self, __context: Any, /) -> None:
        """Validate configuration after initialization."""
        if self.min_players > self.max_players:
            raise ValueError("min_players cannot be greater than max_players")


class BaseGameState(JsonModel, ABC):
    """Base game state for all games."""

    game_id: GameId = Field(..., description="Unique identifier for the game")
    env: GameType = Field(..., description="Type of game")
    turn: int = Field(default=0, description="Current turn number", ge=0)
    is_finished: bool = Field(default=False, description="Whether the game has ended")
    current_player_id: PlayerId = Field(default=NO_PLAYER_ID, description="ID of the player whose turn it is")


class BaseGameEvent(JsonModel, ABC):
    """Base game event for all games."""

    id: EventId = Field(default_factory=lambda: EventId(TSID.create()), description="Unique event ID")
    timestamp: int = Field(default_factory=lambda: int(get_now().timestamp()), description="Event timestamp")
    turn: int = Field(..., description="Game round number")


class BasePlayerViewEvent(JsonModel, ABC):
    """Base player view event that removes sensitive fields and adds display formatting."""

    event: str = Field(..., description="Human-readable event type")  # Subclasses should narrow this to Literal types
    timestamp: int = Field(..., description="Event timestamp")
    turn: int = Field(..., description="Game round number")


class BaseGameStateView(JsonModel, ABC):
    """Base game state view for all games."""

    events: Sequence[BasePlayerViewEvent] = Field(default_factory=list, description="Events visible to this player")


class ReasoningEventMixin(JsonModel):
    """Shared payload for reasoning events across all environments."""

    player_id: PlayerId = Field(..., description="Player ID of the agent")
    reasoning: AgentReasoning = Field(..., description="Agent's reasoning for the action/move")
    tool_calls: list[ExecutedToolCall] = Field(default_factory=list, description="List of tool calls made during decision making")


class ChatMessageMixin(JsonModel):
    """Shared payload for chat message events across all environments."""

    player_id: PlayerId = Field(..., description="Player ID who sent the message")
    message: str = Field(..., description="Chat message content")


class BasePlayerMoveData(JsonModel, ABC):
    """Base player move for all games.

    Note: Reasoning is provided at the top level of AgentDecision, not here.
    """


class BasePlayerPossibleMoves(JsonModel, ABC):
    """Base player possible moves for all games."""


TConfig = TypeVar("TConfig", bound=BaseGameConfig)
TState = TypeVar("TState", bound=BaseGameState)
TEvent = TypeVar("TEvent", bound=BaseGameEvent)
TPlayerMoveData = TypeVar("TPlayerMoveData", bound=BasePlayerMoveData)
TPlayerView = TypeVar("TPlayerView", bound=BaseGameStateView)
TPossibleMoves = TypeVar("TPossibleMoves", bound=BasePlayerPossibleMoves)


class PlayerMove(JsonModel, Generic[TPlayerMoveData]):  # noqa: UP046
    """Base player move for all games."""

    player_id: PlayerId = Field(..., description="ID of the player making the move")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when move was made")
    data: TPlayerMoveData = Field(..., description="Move data")


class ToolCall(JsonModel):
    """Represents a tool call the agent wants to execute."""

    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: dict[str, Any] | None = Field(default=None, description="Parameters for the tool call")


class BaseAgentDecision(JsonModel, ABC, Generic[TPlayerMoveData]):  # noqa: UP046
    """Top-level decision structure returned by the agent each iteration.

    The agent must choose either to call a tool, make a final move, or exit the game, but not multiple.

    Field order matters: reasoning must be provided first, then the action (tool_call/move/exit), then chat_message.
    """

    reasoning: AgentReasoning | None = Field(
        default=None, description="Your reasoning for the action you are about to take (tool call, move, or exit). Explain WHY you chose this specific action."
    )

    # Either make a tool call...
    tool_call: ToolCall | None = Field(default=None, description="Tool to call for gathering information")

    # ...OR make a move
    move: TPlayerMoveData | None = Field(default=None, description="Final move to take in the game")

    # ...OR exit the game
    exit: bool | None = Field(default=None, description="Whether the agent wants to exit the game")

    # Chat message - required only when making a move or exiting, optional for tool calls
    chat_message: str | None = Field(
        default=None,
        description="Message to communicate with other players. REQUIRED when making a move or exiting. Optional (can be null) when calling a tool.",
    )


class EventCollector(Generic[TEvent]):  # noqa: UP046
    """Collects events during game operations."""

    _events: list[TEvent]

    def __init__(self) -> None:
        self._events = []

    def add(self, event: TEvent) -> None:
        self._events.append(event)

    def get_events(self) -> list[TEvent]:
        return self._events.copy()


class GameEnvTypes(ABC, Generic[TState, TPlayerView, TEvent, TPlayerMoveData, TConfig, TPossibleMoves]):  # noqa: UP046
    @classmethod
    @abstractmethod
    def type(cls) -> GameType: ...

    @classmethod
    @abstractmethod
    def config_type(cls) -> type[TConfig]: ...

    @classmethod
    @abstractmethod
    def state_type(cls) -> type[TState]: ...

    @classmethod
    @abstractmethod
    def event_type(cls) -> type[TEvent]: ...

    @classmethod
    @abstractmethod
    def player_move_type(cls) -> type[TPlayerMoveData]: ...

    @classmethod
    @abstractmethod
    def player_view_type(cls) -> type[TPlayerView]: ...

    @classmethod
    @abstractmethod
    def possible_moves_type(cls) -> type[TPossibleMoves]: ...

    @classmethod
    @abstractmethod
    def agent_decision_type(cls) -> type[BaseAgentDecision[TPlayerMoveData]]: ...

    @classmethod
    @abstractmethod
    def reasoning_event_type(cls) -> type[BaseGameEvent]: ...

    @classmethod
    @abstractmethod
    def create_reasoning_event(
        cls, turn: int, player_id: PlayerId, reasoning: AgentReasoning, tool_calls: list[ExecutedToolCall] | None = None
    ) -> BaseGameEvent: ...

    @classmethod
    @abstractmethod
    def create_chat_event(cls, turn: int, player_id: PlayerId, message: str) -> BaseGameEvent: ...

    @classmethod
    @abstractmethod
    def default_config(cls) -> TConfig: ...

    @classmethod
    @abstractmethod
    def config_ui_options(cls) -> dict[str, Any]: ...

    @classmethod
    def supports_spectators(cls) -> bool:
        """Whether this environment supports spectators.

        Default is False; environments should override to enable spectatorship.
        """
        return False

    @classmethod
    def is_analysis_event(cls, event: BaseGameEvent) -> bool:
        """Whether the given event represents a move/position analysis for this environment.

        Default is False; environments that support analysis should override.
        """
        return False


class GameAnalysisHandler(Protocol):
    """Protocol for handling game move analysis across different game types.

    This protocol defines the interface that all game analysis handlers must implement.
    Game environments use this to queue analysis requests in a type-safe, generic way.
    """

    async def queue_analysis(
        self,
        game_id: GameId,
        game_type: GameType,
        round_number: int,
        player_id: PlayerId,
        move_san: str,
        state_before: BaseGameState,
        state_after: BaseGameState,
    ) -> None:
        """Queue a move analysis request.

        Args:
            game_id: The game ID
            game_type: The type of game (chess, poker, etc.)
            round_number: The round/turn number
            player_id: The player who made the move
            move_san: The move in standard notation
            state_before: Game state before the move
            state_after: Game state after the move
        """
        ...


class GameEnv(ABC, Generic[TState, TPlayerView, TEvent, TPlayerMoveData, TConfig, TPossibleMoves]):  # noqa: UP046
    """Abstract base class for game-specific state updates."""

    config: TConfig
    analysis_handler: GameAnalysisHandler

    def __init__(self, config: TConfig, analysis_handler: GameAnalysisHandler) -> None:
        self.config = config
        self.analysis_handler = analysis_handler

    def order_player_ids_for_start(self, player_ids: list[PlayerId]) -> list[PlayerId]:
        """Decide the player order when a game starts.

        Default implementation keeps the original order. Game environments may override
        this to implement environment-specific ordering (e.g., randomize colors in Chess).
        """
        return list(player_ids)

    @classmethod
    @abstractmethod
    def create(
        cls, config: TConfig, analysis_handler: GameAnalysisHandler
    ) -> GameEnv[TState, TPlayerView, TEvent, TPlayerMoveData, TConfig, TPossibleMoves]: ...

    @classmethod
    @abstractmethod
    def types(cls) -> type[GameEnvTypes[TState, TPlayerView, TEvent, TPlayerMoveData, TConfig, TPossibleMoves]]: ...

    @abstractmethod
    def new_game(self, game_id: GameId, event_collector: EventCollector[TEvent]) -> TState:
        """Initialize state for a new game. Returns new state with no players."""

    @abstractmethod
    def new_round(self, prev_state: TState, event_collector: EventCollector[TEvent]) -> TState:
        """Initialize state for a new game round. Returns new state."""

    @abstractmethod
    def join_player(self, state: TState, player_id: PlayerId, event_collector: EventCollector[TEvent], agent_version_id: AgentVersionId, name: str) -> None:
        """Add a player to the game state. Modifies state in place."""

    @abstractmethod
    def apply_move(self, state: TState, move: PlayerMove[TPlayerMoveData], event_collector: EventCollector[TEvent]) -> None:
        """Apply move to the game state. Modifies state in place."""

    @abstractmethod
    def calc_possible_moves(self, state: TState, player_id: PlayerId) -> TPossibleMoves | None:
        """Calculate possible moves for the current player."""

    @abstractmethod
    def get_player_view(self, state: TState, player_id: PlayerId, events: list[TEvent]) -> TPlayerView:
        """Get player view of the game state events."""

    @abstractmethod
    def error_fallback_move(self, state: TState, event_collector: EventCollector[TEvent], player_id: PlayerId) -> TPlayerMoveData:
        """Return a fallback move when agent execution fails."""

    @classmethod
    @abstractmethod
    def get_state_generation_system_prompt(cls) -> str:
        """Get system prompt for LLM-based state generation.

        Override this class method to provide game-specific prompts for state generation.
        Default implementation raises NotImplementedError.
        """

    @classmethod
    @abstractmethod
    def create_state_generation_user_prompt(cls, description: str) -> str:
        """Create user prompt for LLM-based state generation.

        Override this class method to provide game-specific user prompts.
        Default implementation raises NotImplementedError.
        """

    @classmethod
    def get_state_generation_examples(cls) -> list[str]:
        """Environment-specific quick prompts for state generation/editing."""
        return []

    @classmethod
    @abstractmethod
    def get_tool_creation_context(cls) -> Any:
        """Get context for tool creation in this environment.

        Returns:
            ToolCreationContext specialized for this game environment.
            This provides schemas, constraints, best practices, and examples
            for creating tools specific to this game type.
        """
        ...

    @classmethod
    @abstractmethod
    def validate_generated_state(cls, state_data: dict[str, Any]) -> Any:
        """Schema-validate and convert generated state data to the player view model.

        This method should ONLY perform Pydantic model validation/normalization and
        return the resulting player-view object. No domain/legality checks here.
        """

    @classmethod
    @abstractmethod
    def validate_test_json(cls, state_view: Any) -> Any:
        """Perform environment-specific domain validation on already-validated player view.

        Input is the Pydantic player-view model returned by validate_generated_state.
        Implementations should raise ValueError with clear, user-facing messages when
        violations are found. Return the (possibly unchanged) player-view object.
        """

    @classmethod
    def validate_final_action(cls, move: TPlayerMoveData, possible_moves: TPossibleMoves) -> list[str]:
        """Validate a final action against possible moves.

        Default implementation returns empty list (no validation errors).
        Individual game environments can override this to provide custom validation.

        Args:
            move: The move to validate
            possible_moves: The possible moves for the current state

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    @classmethod
    @abstractmethod
    def extract_game_result(cls, state: TState) -> GameResult:
        """Extract game result information from the final state.

        This method provides a standardized way to get winner/draw information
        across different game types for display in game history and UI.

        Args:
            state: The game state (typically final state)

        Returns:
            GameResult with winner/draw information
        """

    def on_player_left(
        self,
        state: TState,
        leaving_player_id: PlayerId,
        event_collector: EventCollector[TEvent],
    ) -> FinishDecision:
        """Handle a player leaving the game.

        Default implementation emits no events and returns CONTINUE.
        Environments should override to emit PlayerLeftEvent and determine finish logic.

        Args:
            state: Current game state
            leaving_player_id: ID of the player who is leaving
            event_collector: Collector for events to emit

        Returns:
            FinishDecision indicating whether game should continue, finish, or be cancelled
        """
        return FinishDecision.CONTINUE

    def finish_due_to_forfeit(
        self,
        state: TState,
        remaining_player_ids: list[PlayerId],
        event_collector: EventCollector[TEvent],
    ) -> None:
        """Finish the game by declaring remaining players as winners.

        Modifies state in place to mark game as finished with appropriate winner(s).
        Default implementation does nothing - environments must override.

        Args:
            state: Game state to modify
            remaining_player_ids: IDs of players still in the game
            event_collector: Collector for any final events
        """
        # Default no-op - environments override as needed


type GenericGameEnv = GameEnv[BaseGameState, BaseGameStateView, BaseGameEvent, BasePlayerMoveData, BaseGameConfig, BasePlayerPossibleMoves]
type GenericGameEnvTypes = GameEnvTypes[BaseGameState, BaseGameStateView, BaseGameEvent, BasePlayerMoveData, BaseGameConfig, BasePlayerPossibleMoves]
type GenericPlayerMove = PlayerMove[BasePlayerMoveData]
type GenericAgentDecision = BaseAgentDecision[BasePlayerMoveData]
