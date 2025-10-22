"""Service for game-related business logic and data transformation.

This service handles:
- Converting SQLAlchemy Game models to Pydantic response objects
- Building player information with ratings and colors
- Filtering reasoning events for privacy
- Game configuration building
- Business logic for game creation
"""

from typing import Any

from chess_game.chess_api import ChessConfig, ChessEvent, ChessPlaygroundOpponent, ChessSide, ChessState
from chess_game.chess_scoring import ChessScoring
from game_api import BaseGameConfig, BaseGameEvent, BaseGameState, GameScoring, GameType, ReasoningEventMixin
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from texas_holdem.texas_holdem_api import TexasHoldemConfig, TexasHoldemEvent, TexasHoldemState
from texas_holdem.texas_holdem_scoring import TexasHoldemScoring

from app.schemas.game import GameStateResponse, PlayerInfo
from common.ids import AgentVersionId, GameId, PlayerId, UserId
from common.utils.utils import get_logger
from shared_db.crud.game import GameDAO
from shared_db.models.game import Game
from shared_db.schemas.agent import AgentStatisticsData

logger = get_logger()


def _get_scoring_class_for_game_type(game_type: GameType) -> type[GameScoring]:
    """Get the scoring class for a given game type."""
    if game_type == GameType.CHESS:
        return ChessScoring
    elif game_type == GameType.TEXAS_HOLDEM:
        return TexasHoldemScoring
    else:
        raise ValueError(f"No scoring class implemented for game type: {game_type}")


class GameService:
    """Service for game-related business logic and data transformation."""

    def __init__(self, game_dao: GameDAO):
        """Initialize the game service.

        Args:
            game_dao: DAO for game database operations
        """
        self._game_dao = game_dao

    @staticmethod
    def parse_game_state(game: Game) -> BaseGameState:
        """Parse game state dict into proper Pydantic model based on game type.

        Args:
            game: SQLAlchemy Game model

        Returns:
            Parsed game state (ChessState or TexasHoldemState)

        Raises:
            ValueError: If game state is empty/None or validation fails
        """
        if not game.state:
            raise ValueError(f"Game {game.id} has empty state")

        if game.game_type == GameType.CHESS:
            return ChessState.model_validate(game.state)
        elif game.game_type == GameType.TEXAS_HOLDEM:
            return TexasHoldemState.model_validate(game.state)
        else:
            raise ValueError(f"Unknown game type: {game.game_type}")

    @staticmethod
    def parse_game_config(game: Game) -> BaseGameConfig:
        """Parse game config dict into proper Pydantic model based on game type.

        Args:
            game: SQLAlchemy Game model

        Returns:
            Parsed game config (ChessConfig or TexasHoldemConfig)
        """
        config_type_map = {
            GameType.CHESS: ChessConfig,
            GameType.TEXAS_HOLDEM: TexasHoldemConfig,
        }

        config_class = config_type_map.get(game.game_type)
        if not config_class:
            raise ValueError(f"Unknown game type: {game.game_type}")

        return config_class.model_validate(game.config or {})

    @staticmethod
    def parse_game_events(game: Game) -> list[BaseGameEvent]:
        """Parse game events dicts into proper Pydantic models based on game type.

        Args:
            game: SQLAlchemy Game model

        Returns:
            List of parsed game events
        """
        if not game.events:
            return []

        event_type_map = {
            GameType.CHESS: ChessEvent,
            GameType.TEXAS_HOLDEM: TexasHoldemEvent,
        }

        event_type = event_type_map.get(game.game_type)
        if not event_type:
            raise ValueError(f"Unknown game type: {game.game_type}")

        event_adapter = TypeAdapter(event_type)
        return [event_adapter.validate_python(event.data) for event in game.events]

    def build_player_info(self, game: Game) -> list[PlayerInfo]:
        """Build player info including ratings for the game type.
        
        Args:
            game: SQLAlchemy Game model with loaded relationships
            
        Returns:
            List of PlayerInfo Pydantic objects
        """
        players: list[PlayerInfo] = []

        # Get the scoring class for this game type
        scoring_class = _get_scoring_class_for_game_type(game.game_type)

        # Get default rating for this game type
        default_rating = scoring_class.get_default_rating()

        # game.game_type is now stored as enum in DB
        game_key = game.game_type

        # For chess games, determine player colors from state
        white_id: PlayerId | None = None
        black_id: PlayerId | None = None
        if game.game_type == GameType.CHESS:
            state_dict = game.state or {}
            try:
                chess_state = ChessState.model_validate(state_dict)
                white_id = chess_state.players[0] if len(chess_state.players) > 0 else None
                black_id = chess_state.players[1] if len(chess_state.players) > 1 else None
            except Exception:
                pass

        for game_player in game.game_players:
            agent = game_player.agent_version.agent

            # Extract rating from agent statistics
            rating: int | None = None
            if agent.statistics:
                stats_data = AgentStatisticsData.model_validate(agent.statistics.statistics)
                game_stats = stats_data.game_ratings.get(game_key)
                rating_value = game_stats.rating if game_stats is not None else default_rating
                # Convert to int if we got a value
                rating = int(rating_value)
            else:
                rating = int(default_rating)

            # Get both username (for matching) and display_name (for UI) from the user
            username: str | None = None
            display_name: str | None = None
            if game_player.user:
                username = game_player.user.username
                try:
                    display_name = game_player.user.display_name
                except Exception:
                    display_name = username

            # Determine color for chess games
            color: ChessSide | None = None
            if game.game_type == GameType.CHESS:
                if white_id is not None and game_player.id == white_id:
                    color = ChessSide.WHITE
                elif black_id is not None and game_player.id == black_id:
                    color = ChessSide.BLACK

            players.append(
                PlayerInfo(
                    id=game_player.id,
                    agent_version_id=game_player.agent_version.id,
                    name=agent.name,
                    username=username,
                    display_name=display_name,
                    rating=rating,
                    color=color,
                )
            )
        return players

    def filter_reasoning_events(
        self,
        events: list[BaseGameEvent],
        game: Game,
        user_id: UserId,
    ) -> list[BaseGameEvent]:
        """Filter reasoning events to only show those from the current user's bots.

        This prevents users from seeing opponent bot reasoning during gameplay and replay,
        maintaining competitive integrity while still showing all other game events.

        Args:
            events: List of parsed game events
            game: SQLAlchemy Game model with loaded relationships
            user_id: Current user ID

        Returns:
            Filtered list of events with opponent reasoning removed
        """
        # Get player IDs that belong to the current user
        user_player_ids = {str(gp.id) for gp in game.game_players if gp.user_id == user_id}

        # Filter events: keep all non-reasoning events, and only reasoning events from user's players
        filtered_events: list[BaseGameEvent] = []
        for event in events:
            # Check if this is a reasoning event by checking if it has ReasoningEventMixin fields
            if isinstance(event, ReasoningEventMixin):
                # Only include if it's from one of the user's players
                if str(event.player_id) in user_player_ids:
                    filtered_events.append(event)
            else:
                # Keep all non-reasoning events
                filtered_events.append(event)

        return filtered_events

    def get_user_player_ids(self, game: Game, user_id: UserId) -> set[str]:
        """Get the set of player IDs that belong to a specific user.
        
        Args:
            game: SQLAlchemy Game model with loaded relationships
            user_id: User ID to filter by
            
        Returns:
            Set of player ID strings belonging to the user
        """
        return {str(gp.id) for gp in game.game_players if gp.user_id == user_id}

    def get_game_players_for_replay(
        self,
        game: Game,
        first_move_player_id: PlayerId | None = None,
    ) -> list[tuple[PlayerId, AgentVersionId, str]]:
        """Get game player information for replay, optionally sorted by first move player.
        
        Args:
            game: SQLAlchemy Game model with loaded relationships
            first_move_player_id: Optional player ID who made the first move (for ordering)
            
        Returns:
            List of tuples (player_id, agent_version_id, agent_name) sorted appropriately
        """
        game_players_list = list(game.game_players)
        if first_move_player_id:
            # Sort players so the first move player (White) is added first
            game_players_list.sort(key=lambda gp: gp.id != first_move_player_id)

        return [
            (gp.id, gp.agent_version_id, gp.agent_version.agent.name)
            for gp in game_players_list
        ]

    async def get_game_state_response(
        self,
        db: AsyncSession,
        game_id: GameId,
        user_id: UserId,
    ) -> GameStateResponse[ChessState, ChessConfig, ChessEvent]:
        """Get a game state response with filtered events.

        Args:
            db: Database session
            game_id: Game ID to fetch
            user_id: User ID for filtering reasoning events

        Returns:
            GameStateResponse with properly typed state, config, and filtered events
        """
        game = await self._game_dao.get(db, game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")

        return self.build_game_state_response(game, user_id)

    def build_game_state_response(
        self,
        game: Game,
        user_id: UserId,
    ) -> GameStateResponse[ChessState, ChessConfig, ChessEvent]:
        """Build a GameStateResponse from a Game model for chess games.

        Args:
            game: SQLAlchemy Game model with loaded relationships
            user_id: User ID for filtering reasoning events

        Returns:
            GameStateResponse with properly typed state, config, and filtered events
        """
        players = self.build_player_info(game)

        # Parse state and config
        state_dict = game.state or {}
        config_dict = game.config or {}
        chess_state = ChessState.model_validate(state_dict)
        chess_config = ChessConfig.model_validate(config_dict)

        # Parse and filter events
        event_adapter = TypeAdapter(ChessEvent)
        chess_events: list[ChessEvent] = [
            event_adapter.validate_python(ev.data)  # type: ignore[arg-type]
            for ev in game.events or []
        ]

        # Filter reasoning events
        filtered_events_base = self.filter_reasoning_events(chess_events, game, user_id)  # type: ignore[arg-type]
        filtered_events = [e for e in filtered_events_base if isinstance(e, ChessEvent)]  # type: ignore[misc]

        return GameStateResponse[ChessState, ChessConfig, ChessEvent](
            id=game.id,
            game_type=game.game_type,
            state=chess_state,
            events=filtered_events,
            config=chess_config,
            version=game.version,
            players=players,
            is_playground=game.is_playground,
        )

    def build_poker_game_state_response(
        self,
        game: Game,
        user_id: UserId | None = None,
    ) -> GameStateResponse[TexasHoldemState, TexasHoldemConfig, TexasHoldemEvent]:
        """Build a GameStateResponse from a Game model for poker games.

        Args:
            game: SQLAlchemy Game model with loaded relationships
            user_id: Optional user ID for filtering reasoning events

        Returns:
            GameStateResponse with properly typed state, config, and events
        """
        players = self.build_player_info(game)

        # Parse state and config
        state_dict = game.state or {}
        config_dict = game.config or {}
        poker_state = TexasHoldemState.model_validate(state_dict)
        poker_config = TexasHoldemConfig.model_validate(config_dict)

        # Parse events
        event_adapter = TypeAdapter(TexasHoldemEvent)
        poker_events: list[TexasHoldemEvent] = [
            event_adapter.validate_python(ev.data)  # type: ignore[arg-type]
            for ev in game.events or []
        ] if game.events else []

        # Filter reasoning events if user_id provided
        if user_id:
            filtered_events_base = self.filter_reasoning_events(poker_events, game, user_id)  # type: ignore[arg-type]
            poker_events = [e for e in filtered_events_base if isinstance(e, TexasHoldemEvent)]  # type: ignore[misc]

        return GameStateResponse[TexasHoldemState, TexasHoldemConfig, TexasHoldemEvent](
            id=game.id,
            game_type=game.game_type,
            state=poker_state,
            events=poker_events,
            config=poker_config,
            version=game.version,
            players=players,
            is_playground=game.is_playground,
        )

    def build_generic_game_state_response(
        self,
        game: Game,
        user_id: UserId,
    ) -> GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent]:
        """Build a generic GameStateResponse from a Game model.

        This method works for any game type and returns base types.
        Use this for endpoints that need to handle multiple game types.

        Args:
            game: SQLAlchemy Game model with loaded relationships
            user_id: User ID for filtering reasoning events

        Returns:
            GameStateResponse with base types
        """
        players = self.build_player_info(game)

        # Parse state, config, and events using generic parsers
        state = self.parse_game_state(game)
        config = self.parse_game_config(game)
        events = self.parse_game_events(game)

        # Filter reasoning events
        filtered_events = self.filter_reasoning_events(events, game, user_id)

        return GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent](
            id=game.id,
            game_type=game.game_type,
            state=state,
            config=config,
            events=filtered_events,
            version=game.version,
            players=players,
            is_playground=game.is_playground,
        )

    @staticmethod
    def build_chess_playground_config(
        base_config: dict[str, Any],
        opponent: ChessPlaygroundOpponent,
        user_side: ChessSide,
    ) -> ChessConfig:
        """Build a chess playground configuration with proper typing.

        Args:
            base_config: Base configuration dictionary
            opponent: Playground opponent type
            user_side: Which side the user plays

        Returns:
            Properly typed ChessConfig
        """
        # Create a new config with playground settings
        config = ChessConfig.model_validate(base_config)

        # Override with playground-specific settings
        config.min_players = 2
        config.max_players = 2
        config.disable_timers = True
        config.playground_opponent = opponent
        config.user_side = user_side

        return config

    @staticmethod
    def derive_chess_agent_ids(
        opponent: ChessPlaygroundOpponent,
        agent_id: AgentVersionId | None,
        brain_bot_agent_version: AgentVersionId,
        user_side: ChessSide = ChessSide.WHITE,
    ) -> list[AgentVersionId]:
        """Determine agent assignments for chess playground.
        
        Args:
            opponent: Type of opponent (self or brain bot)
            agent_id: User's agent version ID
            brain_bot_agent_version: Brain bot agent version ID
            user_side: Which side the user plays (white or black)
            
        Returns:
            List of agent IDs where first agent is white, second is black
            
        Raises:
            ValueError: If agent_id is None
        """
        if agent_id is None:
            raise ValueError("Agent ID is required when creating a chess playground")

        if opponent == ChessPlaygroundOpponent.SELF:
            return [agent_id, agent_id]

        # Brain bot opponent: order agents based on user_side
        if user_side == ChessSide.WHITE:
            return [agent_id, brain_bot_agent_version]
        else:
            return [brain_bot_agent_version, agent_id]

