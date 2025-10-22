"""Chess scoring system using only Elo rating calculations."""

import math
from typing import Any, ClassVar

from game_api import GameResult, GameScoring, PlayerId


class ChessScoring(GameScoring):
    """Chess scoring system using only Elo rating calculations."""

    # Constants for Elo calculations
    DEFAULT_ELO_RATING: ClassVar[int] = 1200
    K_FACTOR_NEW_PLAYER: ClassVar[int] = 40  # For players with < 30 games
    K_FACTOR_NORMAL: ClassVar[int] = 32  # For established players
    K_FACTOR_MASTER: ClassVar[int] = 24  # For players with rating > 2400
    MINIMUM_RATING: ClassVar[int] = 0  # Elo rating cannot go below 0

    @classmethod
    def calculate_player_score(cls, result: GameResult, player_id: PlayerId, opponent_ratings: dict[PlayerId, float]) -> float:
        """Not used - we only track Elo ratings directly."""
        return 0.0

    @classmethod
    def calculate_rating_change(cls, player_rating: float, opponent_rating: float, actual_score: float, k_factor: float = 32) -> float:
        """Calculate Elo rating change using standard formula.

        The Elo formula:
        Expected Score (E) = 1 / (1 + 10^((R_opponent - R_player) / 400))
        New Rating (R') = R + K * (S - E)

        Args:
            player_rating: Current Elo rating of the player
            opponent_rating: Current Elo rating of the opponent
            actual_score: Actual score achieved (1 for win, 0.5 for draw, 0 for loss)
            k_factor: K-factor for rating calculation

        Returns:
            Rating change (positive for gain, negative for loss)
        """
        # Calculate expected score using Elo formula
        rating_difference = opponent_rating - player_rating
        expected_score = 1.0 / (1.0 + math.pow(10.0, rating_difference / 400.0))

        # Calculate rating change
        rating_change = k_factor * (actual_score - expected_score)

        # Round to nearest whole number
        return round(rating_change)

    @classmethod
    def update_rating(cls, current_rating: float, rating_change: float) -> float:
        """Update a player's Elo rating, ensuring it doesn't go below 0.

        Args:
            current_rating: Current Elo rating
            rating_change: Rating change (positive or negative)

        Returns:
            New Elo rating (minimum 0)
        """
        new_rating = current_rating + rating_change
        return max(new_rating, cls.MINIMUM_RATING)

    @classmethod
    def get_default_rating(cls) -> float:
        """Get the default starting Elo rating for new players.

        Returns:
            Default Elo rating of 1200
        """
        return cls.DEFAULT_ELO_RATING

    @classmethod
    def get_k_factor(cls, games_played: int, current_rating: float) -> int:
        """Get appropriate K-factor based on player experience and rating.

        Args:
            games_played: Number of games the player has played
            current_rating: Current Elo rating of the player

        Returns:
            Appropriate K-factor value
        """
        if games_played < 30:
            return cls.K_FACTOR_NEW_PLAYER
        elif current_rating >= 2400:
            return cls.K_FACTOR_MASTER
        else:
            return cls.K_FACTOR_NORMAL

    @classmethod
    def get_score_metrics(cls, result: GameResult, player_id: PlayerId) -> dict[str, Any]:
        """Get chess-specific performance metrics for a player.

        Args:
            result: The game result
            player_id: The player ID to get metrics for

        Returns:
            Dictionary of chess-specific performance metrics
        """
        # Determine result type
        if result.winner_id == player_id or player_id in result.winners_ids:
            result_type = "win"
        elif result.draw_reason is not None:
            result_type = "draw"
        else:
            result_type = "loss"

        return {
            "result_type": result_type,
            "opponent_ids": [pid for pid in result.winners_ids if pid != player_id]
            + ([result.winner_id] if result.winner_id and result.winner_id != player_id else []),
            "was_draw": result.draw_reason is not None,
            "draw_reason": result.draw_reason,
        }

    @classmethod
    def get_result_description(cls, result: GameResult, player_id: PlayerId) -> str:
        """Get human-readable description of the chess result for a player.

        Args:
            result: The game result
            player_id: The player ID to describe result for

        Returns:
            Human-readable result description
        """
        if result.winner_id == player_id or player_id in result.winners_ids:
            return "Win"
        elif result.draw_reason is not None:
            if result.draw_reason:
                return f"Draw ({result.draw_reason})"
            return "Draw"
        else:
            return "Loss"
