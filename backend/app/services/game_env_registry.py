from __future__ import annotations

from typing import Any

from chess_game.chess_env import ChessEnv
from game_api import BaseGameConfig, GameAnalysisHandler, GameType, GenericGameEnv
from texas_holdem.texas_holdem_env import TexasHoldemEnv

from common.utils.utils import cached_classmethod


class GameEnvRegistry:
    _registry: dict[GameType, type[GenericGameEnv]]

    def __init__(self, envs: list[Any]) -> None:
        """Initialize registry with game environment classes.

        Args:
            envs: List of game environment classes (typed as Any to avoid variance issues)
        """
        self._registry = {}
        for env in envs:
            self._register(env)

    def _register(self, env_class: type[GenericGameEnv]) -> None:
        self._registry[env_class.types().type()] = env_class

    def get(self, game_type: GameType) -> type[GenericGameEnv]:
        return self._registry[game_type]

    def create(self, game_type: GameType, config: BaseGameConfig, analysis_handler: GameAnalysisHandler) -> GenericGameEnv:
        """Create a game environment instance.

        Args:
            game_type: The type of game to create
            config: Game configuration
            analysis_handler: Game analysis handler for queueing move analysis

        Returns:
            Game environment instance
        """
        return self.get(game_type).create(config, analysis_handler)

    @cached_classmethod
    def instance(cls) -> GameEnvRegistry:
        return GameEnvRegistry([TexasHoldemEnv, ChessEnv])
