"""SQS message schemas for game turn and analysis processing."""

from typing import Any

from game_api import GameType
from pydantic import Field

from common.core.sqs_client import SqsClient
from common.ids import GameId, PlayerId
from common.utils.json_model import JsonModel


class GameTurnMessage(JsonModel):
    """Message for processing a game turn via SQS."""

    game_id: GameId = Field(..., description="ID of the game")
    player_id: PlayerId = Field(..., description="ID of the player whose turn it is")
    turn: int = Field(..., description="Turn number to validate against the game state")


class GameAnalysisMessage(JsonModel):
    """Message for processing game move analysis via SQS.

    This message contains all the information needed to analyze a move
    across different game environments (chess, poker, etc.).
    State data is stored as dicts to preserve all environment-specific fields.
    """

    game_id: GameId = Field(..., description="ID of the game")
    game_type: GameType = Field(..., description="Type of game (chess, poker, etc.)")
    round_number: int = Field(..., description="Round/turn number")
    player_id: PlayerId = Field(..., description="ID of the player who made the move")
    move_san: str = Field(..., description="Move in standard notation")

    # State data as dicts to preserve all environment-specific fields during serialization
    state_before_data: dict[str, Any] = Field(..., description="Game state before the move as dict")
    state_after_data: dict[str, Any] = Field(..., description="Game state after the move as dict")


# Type aliases for the SQS clients
GameTurnSqsClient = SqsClient[GameTurnMessage]
GameAnalysisSqsClient = SqsClient[GameAnalysisMessage]
