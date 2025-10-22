"""Stockfish-based agent execution service for the Brain bot."""

from typing import Literal, cast

import chess
from chess_game.chess_api import ChessMoveData, ChessStateView
from game_api import BaseGameStateView, BasePlayerPossibleMoves

from app.services.agent_execution_service import AgentExecutionResult
from app.services.stockfish_service import StockfishService
from common.core.app_error import Errors
from common.ids import AgentId
from common.types import AgentReasoning
from common.utils.tsid import TSID
from common.utils.utils import get_logger
from shared_db.schemas.agent import AgentVersionResponse

logger = get_logger()


class StockfishAgentExecutor:
    """Specialized executor for Stockfish-based Brain bot in chess games.

    This service bypasses LLM execution and uses Stockfish engine directly
    for move generation in chess games.
    """

    def __init__(self, stockfish_service: StockfishService) -> None:
        self._stockfish_service = stockfish_service

    async def execute_stockfish_move(
        self,
        agent: AgentVersionResponse,
        game_state: BaseGameStateView,
        possible_moves: BasePlayerPossibleMoves | None,
        opponent_rating: int | None = None,
    ) -> AgentExecutionResult:
        """Execute a move using Stockfish engine for the Brain bot.

        Args:
            agent: Agent version data (should be the Brain bot)
            game_state: Current game state view
            possible_moves: Legal moves for the current position (not used by Stockfish)
            opponent_rating: Opponent's chess rating for adaptive difficulty

        Returns:
            AgentExecutionResult with the Stockfish move
        """
        if not isinstance(game_state, ChessStateView):
            raise ValueError("Stockfish executor can only handle chess game states")

        # Use agent_id as a proxy for game_id since ChessStateView doesn't have game_id
        game_id = f"agent-{agent.agent_id}"
        logger.info(f"Executing Stockfish move for Brain bot in game {game_id}")

        try:
            fen = self._chess_state_to_fen(game_state)
            logger.info("Current position FEN generated for Stockfish", fen=fen)
            board = chess.Board(fen)

            # Calculate adaptive ELO based on opponent rating
            stockfish_elo = self._stockfish_service.get_adaptive_elo(opponent_rating=opponent_rating)
            logger.info(f"Using adaptive Stockfish ELO: {stockfish_elo}")

            # Get best move from Stockfish
            best_move_uci = self._stockfish_service.get_move_from_fen(fen, elo_rating=stockfish_elo)
            if not best_move_uci:
                logger.warning("Stockfish returned no move - game may be over")
                return AgentExecutionResult(
                    move_data=None,
                    exit=False,
                    reasoning=AgentReasoning("No legal moves available"),
                )

            logger.info(f"Stockfish best move: {best_move_uci}")
            uci_move = chess.Move.from_uci(best_move_uci)
            if uci_move not in board.legal_moves:
                raise Errors.Agent.INVALID_OUTPUT.create(
                    message="Stockfish returned an illegal move for the current position",
                    details={"fen": fen, "move": best_move_uci},
                )

            # Create move data
            promotion: Literal["q", "r", "b", "n"] | None = None
            if uci_move.promotion:
                promo_symbol = chess.piece_symbol(uci_move.promotion)
                if promo_symbol in {"q", "r", "b", "n"}:
                    promotion = cast(Literal["q", "r", "b", "n"], promo_symbol)

            # Generate simple reasoning based on Stockfish analysis (no LLM)
            reasoning = self._generate_simple_reasoning(fen, best_move_uci, stockfish_elo)

            move_data = ChessMoveData(
                from_square=best_move_uci[:2],
                to_square=best_move_uci[2:4],
                promotion=promotion,
            )

            return AgentExecutionResult(
                move_data=move_data.to_dict(mode="json"),
                exit=False,
                reasoning=reasoning,
            )

        except Exception as e:
            logger.exception(f"Error executing Stockfish move: {e}")
            # Re-raise to let the game manager handle fallback
            raise

    def _chess_state_to_fen(self, game_state: ChessStateView) -> str:
        """Convert ChessStateView to FEN string for Stockfish."""
        # Convert board map to 2D array for FEN generation
        from chess_game.chess_api import map_to_board

        board_array = map_to_board(game_state.board)

        # Reconstruct FEN from the state view
        board_fen_parts: list[str] = []

        if len(board_array) != 8 or any(len(rank) != 8 for rank in board_array):
            raise ValueError("Chess board must be 8x8 to build FEN")

        for rank_idx in range(8):
            rank_str = ""
            empty_count = 0
            for file_idx in range(8):
                piece = board_array[rank_idx][file_idx]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        rank_str += str(empty_count)
                        empty_count = 0
                    # Convert piece to FEN notation
                    piece_char = piece.type.value[0].lower()
                    if piece.type.value == "knight":
                        piece_char = "n"
                    if piece.color == "white":
                        piece_char = piece_char.upper()
                    rank_str += piece_char
            if empty_count > 0:
                rank_str += str(empty_count)
            board_fen_parts.append(rank_str)

        board_fen = "/".join(board_fen_parts)

        # 2. Active color
        active_color = "w" if game_state.side_to_move == "white" else "b"

        # 3. Castling rights
        castling = ""
        if game_state.castling_rights.white_kingside:
            castling += "K"
        if game_state.castling_rights.white_queenside:
            castling += "Q"
        if game_state.castling_rights.black_kingside:
            castling += "k"
        if game_state.castling_rights.black_queenside:
            castling += "q"
        if not castling:
            castling = "-"

        # 4. En passant square
        en_passant = game_state.en_passant_square or "-"

        # 5. Halfmove clock
        halfmove_clock = str(game_state.halfmove_clock)

        # 6. Fullmove number
        fullmove_number = str(game_state.fullmove_number)

        return f"{board_fen} {active_color} {castling} {en_passant} {halfmove_clock} {fullmove_number}"

    def _generate_simple_reasoning(self, fen: str, move: str, elo: int) -> AgentReasoning:
        """Generate simple reasoning based on Stockfish analysis (no LLM).

        Args:
            fen: FEN string before the move
            move: Move in UCI notation
            elo: ELO rating used for analysis

        Returns:
            Simple reasoning with Stockfish evaluation
        """
        try:
            # Get basic Stockfish analysis
            board = chess.Board(fen)
            move_data = self._stockfish_service.get_best_move(board, elo_rating=elo, time_limit=0.5)

            evaluation = move_data.get("evaluation", "N/A")
            confidence = move_data.get("confidence", 0)

            # Build simple reasoning string
            reasoning_text = f"Stockfish (ELO {elo}): {move} | Eval: {evaluation} | Confidence: {confidence:.1%}"

            return AgentReasoning(reasoning_text)

        except Exception as e:
            logger.warning(f"Failed to generate Stockfish reasoning: {e}")
            # Fallback to minimal reasoning
            return AgentReasoning(f"Stockfish (ELO {elo}): {move}")


# Global instance for Stockfish execution
_stockfish_executor: StockfishAgentExecutor | None = None


def get_stockfish_executor() -> StockfishAgentExecutor:
    """Get global Stockfish executor instance."""
    global _stockfish_executor
    if _stockfish_executor is None:
        stockfish_service = StockfishService()
        _stockfish_executor = StockfishAgentExecutor(stockfish_service)
    return _stockfish_executor


def is_brain_bot_agent(agent: AgentVersionResponse) -> bool:
    """Check if the agent is the Brain bot."""
    # Brain bot has agent_id 800000000000001007
    brain_bot_agent_id = AgentId(TSID(800000000000001007))
    is_brain = agent.agent_id == brain_bot_agent_id
    logger.info(
        f"Brain bot check: agent_id={agent.agent_id}, expected={brain_bot_agent_id}, is_brain={is_brain}",
        agent_id=str(agent.agent_id),
        expected_id=str(brain_bot_agent_id),
        is_brain_bot=is_brain,
    )
    return is_brain


async def execute_brain_bot_move(
    agent: AgentVersionResponse,
    game_state: BaseGameStateView,
    possible_moves: BasePlayerPossibleMoves | None,
    opponent_rating: int | None = None,
) -> AgentExecutionResult | None:
    """Execute a move for the Brain bot using Stockfish.

    Returns None if the agent is not the Brain bot.
    """
    if not is_brain_bot_agent(agent):
        return None

    executor = get_stockfish_executor()
    return await executor.execute_stockfish_move(
        agent=agent,
        game_state=game_state,
        possible_moves=possible_moves,
        opponent_rating=opponent_rating,
    )
