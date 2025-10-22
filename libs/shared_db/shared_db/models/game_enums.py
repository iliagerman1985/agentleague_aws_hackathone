"""Game-related enums for the shared database."""

from game_api import GameType
from pydantic import BaseModel, Field


class GameEnvironmentMetadata(BaseModel):
    """Metadata for a specific game environment."""

    display_name: str
    description: str
    max_players: int
    min_players: int
    supports_spectators: bool
    has_betting: bool
    is_turn_based: bool
    allow_auto_reenter: bool

    # Pricing (token economy)
    real_game_token_cost_per_player: int = Field(description="Tokens charged to each non-system player when joining a real game")
    playground_move_token_cost: int = Field(description="Tokens charged per playground move")

    # Matchmaking fields
    waiting_time_seconds: int = Field(default=60, description="Time to wait for players before starting with system agents")
    supports_midgame_joining: bool = Field(default=False, description="Whether players can join mid-game")


# Game environment metadata registry
GAME_ENVIRONMENT_METADATA: dict[GameType, GameEnvironmentMetadata] = {
    GameType.TEXAS_HOLDEM: GameEnvironmentMetadata(
        display_name="Texas Hold'em Poker",
        description="Classic Texas Hold'em poker with betting rounds and community cards",
        max_players=5,
        min_players=2,
        supports_spectators=True,
        has_betting=True,
        is_turn_based=True,
        allow_auto_reenter=True,
        # Pricing
        real_game_token_cost_per_player=300,
        playground_move_token_cost=10,
        # Matchmaking
        waiting_time_seconds=15,
        supports_midgame_joining=True,
    ),
    GameType.CHESS: GameEnvironmentMetadata(
        display_name="Chess",
        description="Classic chess with perfect information and turn-based play",
        max_players=2,
        min_players=2,
        supports_spectators=True,
        has_betting=False,
        is_turn_based=True,
        allow_auto_reenter=False,
        # Pricing
        real_game_token_cost_per_player=200,
        playground_move_token_cost=10,
        # Matchmaking
        waiting_time_seconds=15,
        supports_midgame_joining=False,
    ),
}


def get_game_environment_metadata(environment: GameType) -> GameEnvironmentMetadata:
    """Get metadata for a game environment."""
    return GAME_ENVIRONMENT_METADATA[environment]


def get_available_game_environments() -> list[GameType]:
    """Get list of all available game environments."""
    return list(GameType)
