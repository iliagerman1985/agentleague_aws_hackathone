"""Texas Hold'em poker scoring system."""

from typing import Any, ClassVar

from game_api import GameResult, GameScoring, PlayerId


class TexasHoldemScoring(GameScoring):
    """Texas Hold'em scoring system based on tournament-style placement."""

    # Constants for poker scoring
    DEFAULT_POKER_RATING: ClassVar[int] = 1000
    MINIMUM_RATING: ClassVar[int] = 0

    @classmethod
    def calculate_player_score(cls, result: GameResult, player_id: PlayerId, opponent_ratings: dict[PlayerId, float]) -> float:
        """Not used - we only track poker ratings directly."""
        return 0.0

    @classmethod
    def calculate_rating_change(cls, player_rating: float, opponent_rating: float, actual_score: float, k_factor: float = 32) -> float:
        """Calculate poker rating change based on performance.

        Args:
            player_rating: Current poker rating of the player
            opponent_rating: Current poker rating of the opponent (not used in poker)
            actual_score: Final chip count relative to starting stack
            k_factor: K-factor for rating calculation

        Returns:
            Rating change (positive for gain, negative for loss)
        """
        # Simple poker scoring: rating change based on chip performance
        # Positive score = gain chips, Negative score = lose chips
        rating_change = (actual_score - 1.0) * k_factor  # 1.0 = starting stack

        return round(rating_change)

    @classmethod
    def update_rating(cls, current_rating: float, rating_change: float) -> float:
        """Update a player's poker rating, ensuring it doesn't go below 0.

        Args:
            current_rating: Current poker rating
            rating_change: Rating change (positive or negative)

        Returns:
            New poker rating (minimum 0)
        """
        new_rating = current_rating + rating_change
        return max(new_rating, cls.MINIMUM_RATING)

    @classmethod
    def get_default_rating(cls) -> float:
        """Get the default starting poker rating for new players.

        Returns:
            Default poker rating of 1000
        """
        return cls.DEFAULT_POKER_RATING

    @classmethod
    def get_score_metrics(cls, result: GameResult, player_id: PlayerId) -> dict[str, Any]:
        """Get poker-specific performance metrics for a player.

        Args:
            result: The game result
            player_id: The player ID to get metrics for

        Returns:
            Dictionary of poker-specific performance metrics
        """
        # Get final chip count if available
        final_chips = 0
        if result.final_scores and player_id in result.final_scores:
            final_chips = result.final_scores[player_id]

        # Determine placement
        if result.winner_id == player_id or player_id in result.winners_ids:
            placement = 1
        else:
            # For simplicity, assume non-winners are tied for last
            placement = 2

        return {
            "final_chips": final_chips,
            "placement": placement,
            "is_winner": placement == 1,
            "opponent_ids": [pid for pid in result.winners_ids if pid != player_id]
            + ([result.winner_id] if result.winner_id and result.winner_id != player_id else []),
        }

    @classmethod
    def get_result_description(cls, result: GameResult, player_id: PlayerId) -> str:
        """Get human-readable description of the poker result for a player.

        Args:
            result: The game result
            player_id: The player ID to describe result for

        Returns:
            Human-readable result description
        """
        if result.winner_id == player_id or player_id in result.winners_ids:
            return "Win"
        else:
            return "Loss"
