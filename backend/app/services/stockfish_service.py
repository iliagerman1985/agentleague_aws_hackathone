"""Comprehensive Stockfish engine service for chess gameplay and analysis.

This service consolidates all Stockfish-related functionality from existing services,
providing a unified interface for:
1. Move generation for the Brain bot (adaptive difficulty)
2. Move analysis for game analysis
3. Position evaluation and assessment
4. Skill level adjustment based on opponent ratings
"""

from __future__ import annotations

from typing import Any, Literal

import chess
import chess.engine

from common.utils.utils import get_logger

logger = get_logger()


class StockfishService:
    """Unified Stockfish service for chess engine operations."""

    def __init__(self, stockfish_path: str | None = None):
        """Initialize Stockfish service.

        Args:
            stockfish_path: Path to Stockfish executable. If None, assumes 'stockfish' is in PATH.
        """
        self.stockfish_path = stockfish_path or "stockfish"
        self._engine: chess.engine.SimpleEngine | None = None
        self._is_initialized = False

    def _ensure_engine(self) -> None:
        """Ensure Stockfish engine is initialized."""
        if not self._is_initialized:
            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
                self._is_initialized = True
                logger.info(
                    "Stockfish engine initialized successfully",
                    operation="stockfish_init",
                    stockfish_path=self.stockfish_path,
                )
            except Exception as e:
                logger.exception(
                    "Failed to initialize Stockfish engine",
                    operation="stockfish_init",
                    error=str(e),
                )
                raise RuntimeError(f"Stockfish engine initialization failed: {e}")

    def close(self) -> None:
        """Close the Stockfish engine."""
        if self._engine:
            try:
                self._engine.quit()
                self._engine = None
                self._is_initialized = False
                logger.info("Stockfish engine closed", operation="stockfish_close")
            except Exception as e:
                logger.warning(
                    "Error closing Stockfish engine",
                    operation="stockfish_close",
                    error=str(e),
                )

    def get_best_move(
        self, board: chess.Board, elo_rating: int = 1200, time_limit: float = 1.0, depth: int = 15, analysis_mode: Literal["move", "analysis"] = "move"
    ) -> dict[str, Any]:
        """Get the best move from Stockfish engine.

        Args:
            board: Current chess board position
            elo_rating: Target ELO rating for difficulty adjustment
            time_limit: Time limit for engine analysis in seconds
            depth: Search depth for analysis
            analysis_mode: Mode of operation ("move" or "analysis")

        Returns:
            Dictionary containing:
            - best_move: Best move in UCI notation (e.g., "e2e4")
            - confidence: Move confidence score (0.0-1.0)
            - evaluation: Position evaluation in centipawns
            - depth: Search depth reached
            - nodes: Number of nodes searched
            - time: Analysis time in milliseconds
            - skill_level: Calculated skill level (0-20)
        """
        self._ensure_engine()
        if not self._engine:
            raise RuntimeError("Stockfish engine not available")

        try:
            # Configure engine parameters
            if analysis_mode == "move":
                limit = chess.engine.Limit(time=time_limit, depth=depth)
            else:
                limit = chess.engine.Limit(time=time_limit, depth=depth)

            logger.info(
                f"Requesting {analysis_mode} from Stockfish",
                operation="stockfish_move",
                elo_rating=elo_rating,
                depth=depth,
                time_limit=time_limit,
                fen=board.fen(),
            )

            # Get best move from Stockfish
            result = self._engine.play(board, limit)

            # Get position evaluation
            info = self._engine.analyse(board, limit)
            evaluation = self._extract_evaluation(info)

            # Calculate confidence based on evaluation and skill level
            skill_level = self._calculate_skill_level(elo_rating)
            confidence = self._calculate_confidence(evaluation, skill_level)

            move_data = {
                "best_move": result.move.uci(),
                "confidence": confidence,
                "evaluation": evaluation,
                "depth": info.get("depth", 0),
                "nodes": info.get("nodes", 0),
                "time": info.get("time", 0.0),
                "skill_level": skill_level,
                "analysis_mode": analysis_mode,
            }

            logger.info(
                f"Stockfish {analysis_mode} completed",
                operation="stockfish_move",
                best_move=move_data["best_move"],
                evaluation=move_data["evaluation"],
                depth=move_data["depth"],
                confidence=move_data["confidence"],
            )

            return move_data

        except Exception as e:
            logger.exception(
                f"Error getting {analysis_mode} from Stockfish",
                operation="stockfish_move",
                error=str(e),
                fen=board.fen(),
            )
            raise RuntimeError(f"Stockfish {analysis_mode} failed: {e}")

    def analyze_position(self, board: chess.Board, time_limit: float = 1.0, depth: int = 15) -> dict[str, Any]:
        """Analyze the current position using Stockfish.

        Args:
            board: Current chess board position
            time_limit: Time limit for analysis in seconds
            depth: Search depth for analysis

        Returns:
            Dictionary containing position analysis data
        """
        self._ensure_engine()
        if not self._engine:
            raise RuntimeError("Stockfish engine not available")

        try:
            limit = chess.engine.Limit(time_limit=time_limit, depth=depth)
            info = self._engine.analyse(board, limit)

            return {
                "evaluation": self._extract_evaluation(info),
                "depth": info.get("depth", 0),
                "nodes": info.get("nodes", 0),
                "time": info.get("time", 0.0),
                "pv": info.get("pv", []),
                "mate": self._extract_mate_score(info),
                "best_move": None,
                "variation": None,
            }

        except Exception as e:
            logger.exception(
                "Error analyzing position with Stockfish",
                operation="stockfish_analyze",
                error=str(e),
                fen=board.fen(),
            )
            raise RuntimeError(f"Stockfish position analysis failed: {e}")

    def _extract_evaluation(self, info: dict[str, Any]) -> int:
        """Extract evaluation from Stockfish analysis info.

        Args:
            info: Stockfish analysis info dictionary

        Returns:
            Evaluation in centipawns (positive = white advantage, negative = black advantage)
        """
        if "score" in info:
            score = info["score"]
            white_score = score.white()
            if white_score.is_mate():
                mate_in = white_score.mate()
                if mate_in is None:
                    return 0
                # Convert mate scores to large centipawn values
                cp_value = 10000 if mate_in > 0 else -10000
            else:
                cp_value = white_score.score()
                if cp_value is None:
                    return 0
            return cp_value
        return 0

    def _extract_mate_score(self, info: dict[str, Any]) -> int | None:
        """Extract mate-in-N value from score.

        Args:
            info: Stockfish analysis info dictionary

        Returns:
            Mate-in-N value or None if no mate found
        """
        if "score" in info:
            score = info["score"]
            white_score = score.white()
            if white_score.is_mate():
                return white_score.mate()
        return None

    def _calculate_skill_level(self, elo_rating: int) -> int:
        """Calculate Stockfish skill level based on ELO rating.

        Args:
            elo_rating: Target ELO rating

        Returns:
            Stockfish skill level (0-20)
        """
        # Map ELO ratings to Stockfish skill levels
        if elo_rating <= 800:
            return 0  # Very easy - beginner
        elif elo_rating <= 1000:
            return 1  # Easy
        elif elo_rating <= 1200:
            return 3  # Easy-medium
        elif elo_rating <= 1400:
            return 5  # Medium
        elif elo_rating <= 1600:
            return 8  # Medium-hard
        elif elo_rating <= 1800:
            return 12  # Hard
        elif elo_rating <= 2000:
            return 16  # Very hard
        else:
            return 20  # Maximum difficulty

    def _calculate_confidence(self, evaluation: int, skill_level: int) -> float:
        """Calculate move confidence based on evaluation and skill level.

        Args:
            evaluation: Position evaluation in centipawns
            skill_level: Stockfish skill level (0-20)

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence on evaluation magnitude and skill level
        eval_magnitude = min(abs(evaluation) / 1000.0, 1.0)
        skill_confidence = skill_level / 20.0  # Normalize to 0-1

        # Combine both factors
        confidence = (eval_magnitude + skill_confidence) / 2.0
        return min(max(confidence, 0.1), 1.0)

    def get_adaptive_elo(self, opponent_rating: int | None = None) -> int:
        """Calculate adaptive ELO rating for balanced gameplay.

        Args:
            opponent_rating: The opponent's chess rating

        Returns:
            Adaptive ELO rating for Stockfish
        """
        # Default rating if no opponent rating provided
        if opponent_rating is None:
            return 1200

        # Adaptive difficulty calculation based on opponent rating
        if opponent_rating < 1000:
            adaptive_elo = opponent_rating + 200
        elif opponent_rating <= 1500:
            adaptive_elo = opponent_rating + 150
        else:
            adaptive_elo = opponent_rating + 100

        # Clamp to reasonable range
        return max(800, min(2000, adaptive_elo))

    def get_move_from_fen(self, fen: str, elo_rating: int = 1200, time_limit: float = 1.0) -> str:
        """Get the best move from a FEN position.

        Args:
            fen: FEN string representation of the position
            elo_rating: Target ELO rating for difficulty adjustment
            time_limit: Time limit for engine analysis in seconds

        Returns:
            Best move in UCI notation (e.g., "e2e4")
        """
        board = chess.Board(fen)
        move_data = self.get_best_move(board, elo_rating, time_limit)
        return move_data["best_move"]

    def get_move_analysis(
        self,
        fen: str,
        move: str,
        elo: int = 1200,
    ) -> dict[str, Any]:
        """Analyze a specific move using Stockfish.

        Args:
            fen: FEN string before the move
            move: Move in UCI notation
            elo: ELO rating for analysis

        Returns:
            Move analysis data with evaluation and narrative
        """
        board = chess.Board(fen)

        # Get position evaluation before move
        before_analysis = self.analyze_position(board, time_limit=0.5)

        # Apply the move and analyze after
        try:
            chess_move = chess.Move.from_uci(move)
            if chess_move in board.legal_moves:
                board.push(chess_move)
                after_analysis = self.analyze_position(board, time_limit=0.5)
            else:
                return {"error": "Illegal move"}
        except ValueError:
            return {"error": "Invalid move format"}

        # Calculate evaluation change
        eval_before = before_analysis.get("evaluation", 0)
        eval_after = after_analysis.get("evaluation", 0)

        return {
            "evaluation": eval_after,
            "evaluation_change": eval_after - eval_before,
            "best_move": self.get_best_move(board, elo, time_limit=0.5)["best_move"],
            "variations": [move] if board.pseudo_legal_moves else [],
        }

    def __enter__(self) -> StockfishService:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


# Singleton instance for application-wide use
_stockfish_service: StockfishService | None = None


def get_stockfish_service() -> StockfishService:
    """Get or create the singleton Stockfish service instance."""
    global _stockfish_service
    if _stockfish_service is None:
        _stockfish_service = StockfishService()
    return _stockfish_service


def close_stockfish_service() -> None:
    """Close the singleton Stockfish service."""
    global _stockfish_service
    if _stockfish_service:
        _stockfish_service.close()
        _stockfish_service = None
