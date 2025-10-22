from __future__ import annotations

import random
import time
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, cast, override

import chess as _pychess
from chess_game.chess_api import (
    AgentForfeitEvent,
    AgentForfeitPlayerViewEvent,
    AgentReasoningEvent,
    AgentReasoningPlayerViewEvent,
    CastlingRights,
    ChatMessageEvent,
    ChatMessagePlayerViewEvent,
    CheckEvent,
    CheckmateEvent,
    CheckmatePlayerViewEvent,
    CheckPlayerViewEvent,
    ChessAgentDecision,
    ChessBoardMap,
    ChessConfig,
    ChessEvent,
    ChessMoveData,
    ChessPiece,
    ChessPlayerViewEvent,
    ChessPossibleMove,
    ChessPossibleMoves,
    ChessState,
    ChessStateView,
    ChessTimeControl,
    Color,
    DrawReason,
    GameFinishedEvent,
    GameFinishedPlayerViewEvent,
    GameInitializedEvent,
    MoveAnalysisEvent,
    MovePlayedEvent,
    MovePlayedPlayerViewEvent,
    PieceType,
    PlayerJoinedEvent,
    PlayerJoinedPlayerViewEvent,
    PlayerLeftEvent,
    PlayerLeftPlayerViewEvent,
    StalemateEvent,
    StalematePlayerViewEvent,
    board_to_map,
    create_starting_board,
    map_to_board,
)
from game_api import (
    NO_PLAYER_ID,
    BaseGameEvent,
    EnumOption,
    EventCollector,
    FinishDecision,
    GameAnalysisHandler,
    GameConfigOption,
    GameEnv,
    GameEnvTypes,
    GameId,
    GameResult,
    GameType,
    PlayerId,
    PlayerMove,
)

from common.core.app_error import Errors
from common.ids import AgentVersionId
from common.types import AgentReasoning, ExecutedToolCall
from common.utils.utils import get_logger


class PieceDisplayName(StrEnum):
    """Display names for chess pieces."""

    PAWN = "pawn"
    ROOK = "rook"
    KNIGHT = "knight"
    BISHOP = "bishop"
    QUEEN = "queen"
    KING = "king"


# All chess logic is now handled by python-chess library


class ChessEnvTypes(GameEnvTypes[ChessState, ChessStateView, ChessEvent, ChessMoveData, ChessConfig, ChessPossibleMoves]):
    @classmethod
    def type(cls) -> GameType:
        return GameType.CHESS

    @classmethod
    def config_type(cls) -> type[ChessConfig]:
        return ChessConfig

    @classmethod
    def state_type(cls) -> type[ChessState]:
        return ChessState

    @classmethod
    def event_type(cls) -> type[ChessEvent]:
        return ChessEvent  # type: ignore[return-value]

    @classmethod
    def player_move_type(cls) -> type[ChessMoveData]:
        return ChessMoveData

    @classmethod
    def player_view_type(cls) -> type[ChessStateView]:
        return ChessStateView

    @classmethod
    def possible_moves_type(cls) -> type[ChessPossibleMoves]:
        return ChessPossibleMoves

    @classmethod
    def agent_decision_type(cls) -> type[ChessAgentDecision]:
        return ChessAgentDecision

    @classmethod
    def reasoning_event_type(cls) -> type[BaseGameEvent]:
        return AgentReasoningEvent

    @classmethod
    def supports_spectators(cls) -> bool:
        return True

    @classmethod
    def is_analysis_event(cls, event: BaseGameEvent) -> bool:
        return isinstance(event, MoveAnalysisEvent)

    @classmethod
    def create_reasoning_event(
        cls, turn: int, player_id: PlayerId, reasoning: AgentReasoning, tool_calls: list[ExecutedToolCall] | None = None
    ) -> BaseGameEvent:
        return AgentReasoningEvent(
            turn=turn,
            player_id=player_id,
            reasoning=reasoning,
            tool_calls=tool_calls or [],
        )

    @classmethod
    def create_chat_event(cls, turn: int, player_id: PlayerId, message: str) -> BaseGameEvent:
        return ChatMessageEvent(
            turn=turn,
            player_id=player_id,
            message=message,
        )

    @classmethod
    def default_config(cls) -> ChessConfig:
        return ChessConfig()

    @classmethod
    def config_ui_options(cls) -> dict[str, Any]:
        return {
            "time_control": GameConfigOption(
                type="enum",
                options=[
                    EnumOption(value=ChessTimeControl.LONG.value, label="Long (20 minutes)", default=True),
                    EnumOption(value=ChessTimeControl.BLITZ.value, label="Blitz (10 minutes)", default=False),
                ],
            )
        }


class ChessEnv(GameEnv[ChessState, ChessStateView, ChessEvent, ChessMoveData, ChessConfig, ChessPossibleMoves]):
    def __init__(self, config: ChessConfig, analysis_handler: GameAnalysisHandler) -> None:
        super().__init__(config, analysis_handler)

    def order_player_ids_for_start(self, player_ids: list[PlayerId]) -> list[PlayerId]:
        """Randomize player order at start so colors are randomized (white/black).

        This only affects environments that call this hook during game initialization.
        """
        ids = list(player_ids)
        random.shuffle(ids)
        return ids

    @override
    @classmethod
    def create(cls, config: ChessConfig, analysis_handler: GameAnalysisHandler) -> ChessEnv:
        """Create a ChessEnv instance with analysis handler.

        Args:
            config: Chess game configuration
            analysis_handler: SQS game analysis handler for move analysis

        Returns:
            ChessEnv instance
        """
        return ChessEnv(config, analysis_handler)

    @override
    @classmethod
    def types(
        cls,
    ) -> type[GameEnvTypes[ChessState, ChessStateView, ChessEvent, ChessMoveData, ChessConfig, ChessPossibleMoves]]:
        return ChessEnvTypes

    @override
    def new_game(self, game_id: GameId, event_collector: EventCollector[ChessEvent]) -> ChessState:
        now_ms = int(time.time() * 1000)

        # Create basic game state without players
        state = ChessState(
            game_id=game_id,
            env=self.config.env,
            current_player_id=NO_PLAYER_ID,  # Set to system player initially
            turn=1,
            board=create_starting_board(),
            side_to_move=Color.WHITE,
            castling_rights=CastlingRights(),
            en_passant_square=None,
            halfmove_clock=0,
            fullmove_number=1,
            players=[],  # No players initially
            remaining_time_ms={},  # Will be populated when players join
            last_timestamp_ms=now_ms,
        )

        # Initialize the internal chess board from starting position
        state.chess_board_internal = _pychess.Board()  # Standard starting position

        # Initialize captured pieces (empty at start)
        state.calculate_captured_pieces()

        event_collector.add(GameInitializedEvent(turn=state.turn, game_id=game_id))
        return state

    # -----------------------------
    # Helper methods
    # -----------------------------
    def _other_player_id(self, state: ChessState, player_id: PlayerId) -> PlayerId:
        # Chess always has exactly 2 players, so we can find the other player
        # by looking at the players list
        for pid in state.players:
            if pid != player_id:
                return pid
        raise ValueError(f"No opponent player found. Current player: {player_id}, players in game: {state.players}")

    def _state_to_python_chess_board(self, state: ChessState) -> Any:
        """Convert our ChessState to a python-chess Board object."""

        # Build FEN string from our state
        fen_parts: list[str] = []

        # 1. Piece placement (from rank 8 to rank 1)
        board_fen: list[str] = []
        for rank_idx in range(8):  # Our board[0] = rank 8, board[7] = rank 1
            rank_str = ""
            empty_count = 0
            for file_idx in range(8):
                piece = state.board[rank_idx][file_idx]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        rank_str += str(empty_count)
                        empty_count = 0
                    # Convert our piece to FEN notation
                    piece_char = piece.type.value[0].lower()  # k, q, r, b, n, p
                    if piece.type == PieceType.KNIGHT:
                        piece_char = "n"
                    if piece.color == Color.WHITE:
                        piece_char = piece_char.upper()
                    rank_str += piece_char
            if empty_count > 0:
                rank_str += str(empty_count)
            board_fen.append(rank_str)
        fen_parts.append("/".join(board_fen))

        # 2. Active color
        fen_parts.append("w" if state.side_to_move == Color.WHITE else "b")

        # 3. Castling rights
        castling = ""
        if state.castling_rights.white_kingside:
            castling += "K"
        if state.castling_rights.white_queenside:
            castling += "Q"
        if state.castling_rights.black_kingside:
            castling += "k"
        if state.castling_rights.black_queenside:
            castling += "q"
        fen_parts.append(castling if castling else "-")

        # 4. En passant square
        fen_parts.append(state.en_passant_square if state.en_passant_square else "-")

        # 5. Halfmove clock
        fen_parts.append(str(state.halfmove_clock))

        # 6. Fullmove number
        fen_parts.append(str(state.fullmove_number))

        fen = " ".join(fen_parts)
        return _pychess.Board(fen)

    def _is_move_legal(self, state: ChessState, move_data: ChessMoveData) -> bool:
        """Check if a move is legal using python-chess."""
        try:
            # Use the internal chess board for better performance
            chess_board = state.get_chess_board()
            from_sq = _pychess.parse_square(move_data.from_square)
            to_sq = _pychess.parse_square(move_data.to_square)

            if move_data.promotion:
                promo_map = {"q": _pychess.QUEEN, "r": _pychess.ROOK, "b": _pychess.BISHOP, "n": _pychess.KNIGHT}
                if move_data.promotion not in promo_map:
                    return False
                move = _pychess.Move(from_sq, to_sq, promotion=promo_map[move_data.promotion])
            else:
                move = _pychess.Move(from_sq, to_sq)

            return move in chess_board.legal_moves
        except Exception:
            return False

    def _diagnose_illegal_move(self, state: ChessState, from_square: str, to_square: str, promotion: str | None = None) -> str:
        """Diagnose why a move is illegal using python-chess and provide helpful feedback for the LLM."""

        try:
            # Use the internal chess board for better performance
            chess_board = state.get_chess_board()
        except Exception as e:
            return f"Illegal move: Could not parse current board state: {e}"

        try:
            # Parse squares
            from_sq = _pychess.parse_square(from_square)
            to_sq = _pychess.parse_square(to_square)
        except Exception:
            return f"Illegal move: Invalid square notation. Use format like 'e2' to 'e4'. From: '{from_square}', To: '{to_square}'"

        # Check if there's a piece on the from square
        piece = chess_board.piece_at(from_sq)
        if piece is None:
            return f"Illegal move: No piece on {from_square}. You must move a piece that exists on the board."

        # Check if it's the right color's turn
        if piece.color != chess_board.turn:
            color_name = "White" if chess_board.turn == _pychess.WHITE else "Black"
            piece_color = "white" if piece.color == _pychess.WHITE else "black"
            piece_name = piece.symbol().lower()
            piece_names = {"p": "pawn", "r": "rook", "n": "knight", "b": "bishop", "q": "queen", "k": "king"}
            return f"Illegal move: It's {color_name}'s turn, but you're trying to move a {piece_color} {piece_names.get(piece_name, piece_name)}."

        # Try to create the move
        try:
            if promotion:
                # Map our promotion notation to python-chess
                promo_map = {"q": _pychess.QUEEN, "r": _pychess.ROOK, "b": _pychess.BISHOP, "n": _pychess.KNIGHT}
                if promotion not in promo_map:
                    return f"Illegal move: Invalid promotion piece '{promotion}'. Use 'q', 'r', 'b', or 'n'."
                move = _pychess.Move(from_sq, to_sq, promotion=promo_map[promotion])
            else:
                move = _pychess.Move(from_sq, to_sq)
        except Exception as e:
            return f"Illegal move: Could not create move: {e}"

        # Check if the move is legal
        if move not in chess_board.legal_moves:
            # Try to give more specific feedback
            piece_name = piece.symbol().lower()
            piece_names = {
                "p": PieceDisplayName.PAWN,
                "r": PieceDisplayName.ROOK,
                "n": PieceDisplayName.KNIGHT,
                "b": PieceDisplayName.BISHOP,
                "q": PieceDisplayName.QUEEN,
                "k": PieceDisplayName.KING,
            }
            piece_display = piece_names.get(piece_name, piece_name)

            # Check if it's a pseudo-legal move (follows piece rules but might leave king in check)
            if move in chess_board.pseudo_legal_moves:
                return f"Illegal move: Moving {piece_display} from {from_square} to {to_square} would leave your king in check. You must protect your king."
            else:
                piece_title = piece_display.title() if piece_display else "Piece"
                return f"Illegal move: {piece_title} on {from_square} cannot move to {to_square}. This violates the {piece_display}'s movement rules."

        # This shouldn't happen if our logic is correct
        return f"Illegal move: {from_square} to {to_square} is not allowed."

    @override
    def new_round(self, prev_state: ChessState, event_collector: EventCollector[ChessEvent]) -> ChessState:
        # Chess has no betting rounds; return state unchanged (could also raise if unused in flow)
        return prev_state

    @override
    def join_player(
        self, state: ChessState, player_id: PlayerId, event_collector: EventCollector[ChessEvent], agent_version_id: AgentVersionId, name: str
    ) -> None:
        """Add a player to the chess game state."""
        if len(state.players) >= 2:
            raise ValueError("Chess game already has maximum number of players (2)")

        # Add player to the players list
        state.players.append(player_id)

        # Initialize clock for this player (only for timing purposes, not player tracking)
        if self.config.disable_timers:
            # When timers are disabled, set a dummy value for consistency
            state.remaining_time_ms[player_id] = 0
        else:
            init_ms = 600_000 if self.config.time_control == ChessTimeControl.BLITZ else 1_200_000
            state.remaining_time_ms[player_id] = init_ms

            logger = get_logger()
            logger.info(
                "Initialized chess clock for player",
                player_id=str(player_id),
                time_control=self.config.time_control,
                init_ms=init_ms,
                init_minutes=init_ms / 60_000,
            )

        # Set current player if this is the first player
        if state.current_player_id == NO_PLAYER_ID:
            state.current_player_id = player_id

        # Emit PlayerJoinedEvent
        event_collector.add(
            PlayerJoinedEvent(
                turn=state.turn,
                player_id=player_id,
                agent_version_id=agent_version_id,
                name=name,
            )
        )

    @override
    def apply_move(self, state: ChessState, move: PlayerMove[ChessMoveData], event_collector: EventCollector[ChessEvent]) -> None:
        if state.is_finished:
            raise Errors.Game.ALREADY_FINISHED.create(details={"player_id": move.player_id})
        if move.player_id != state.current_player_id:
            raise Errors.Game.NOT_PLAYER_MOVE.create(details={"player_id": move.player_id, "expected_player_id": state.current_player_id})
        # Handle timing first
        self._handle_timing_update(state, move.player_id, event_collector)
        if state.is_finished:  # Game ended due to timeout
            return

        # Use python-chess for all move logic
        self._apply_move_with_python_chess(state, move, event_collector)

    def check_timeout(self, state: ChessState, event_collector: EventCollector[ChessEvent]) -> bool:
        """Check if current player has run out of time and end game if so.

        Returns:
            True if timeout occurred and game was ended, False otherwise
        """
        if state.is_finished or self.config.disable_timers:
            return False

        last_ts = state.last_timestamp_ms
        if last_ts is None:
            return False

        now_ms = int(time.time() * 1000)
        remaining = dict(state.remaining_time_ms)
        elapsed = max(0, now_ms - last_ts)
        cur_left = remaining.get(state.current_player_id, 0) - elapsed

        # Add debug logging for timeout check
        logger = get_logger(__name__)
        logger.info(
            "Timeout check",
            game_id=str(state.game_id),
            current_player_id=str(state.current_player_id),
            last_timestamp_ms=last_ts,
            now_ms=now_ms,
            elapsed_ms=elapsed,
            remaining_time_ms=remaining.get(state.current_player_id, 0),
            calculated_remaining_ms=cur_left,
            time_control=self.config.time_control,
            disable_timers=self.config.disable_timers,
        )

        # Check if timeout should occur
        if cur_left <= 0:
            # Time forfeit reached: check opponent's mating material per FIDE edge case
            from chess_game.chess_api import ForfeitReason

            opp_pid = self._other_player_id(state, state.current_player_id)
            chess_board = state.get_chess_board()

            # Use python-chess to check insufficient material
            if chess_board.has_insufficient_material(not chess_board.turn):
                winner = None
                reason = DrawReason.TIMEOUT_INSUFFICIENT_MATERIAL
                forfeit_reason = None
            else:
                winner = opp_pid
                reason = DrawReason.TIME
                forfeit_reason = ForfeitReason.TIMEOUT

            # Update remaining time to reflect the timeout (set to 0 if negative)
            if cur_left < 0:
                remaining[state.current_player_id] = 0
                state.remaining_time_ms = remaining

            state.last_timestamp_ms = None
            state.winner = winner
            state.draw_reason = reason
            state.forfeit_reason = forfeit_reason
            state.is_finished = True
            event_collector.add(
                GameFinishedEvent(
                    turn=state.turn,
                    timestamp=int(datetime.now(UTC).timestamp() * 1000),
                    winner=winner,
                    draw_reason=reason,
                    forfeit_reason=forfeit_reason,
                )
            )
            return True

        return False

    def _handle_timing_update(self, state: ChessState, player_id: PlayerId, event_collector: EventCollector[ChessEvent]) -> None:
        """Handle clock updates and timeout detection."""
        now_ms = int(time.time() * 1000) if not self.config.disable_timers else None
        remaining = dict(state.remaining_time_ms)
        last_ts = state.last_timestamp_ms

        if (not self.config.disable_timers) and (last_ts is not None):
            from chess_game.chess_api import ForfeitReason

            elapsed = max(0, int(now_ms or 0) - int(last_ts))
            cur_left = remaining.get(state.current_player_id, 0) - elapsed
            if cur_left <= 0:
                # Time forfeit reached: check opponent's mating material per FIDE edge case
                opp_pid = self._other_player_id(state, state.current_player_id)
                chess_board = state.get_chess_board()

                # Use python-chess to check insufficient material
                if chess_board.has_insufficient_material(not chess_board.turn):
                    winner = None
                    reason = DrawReason.TIMEOUT_INSUFFICIENT_MATERIAL
                    forfeit_reason = None
                else:
                    winner = opp_pid
                    reason = DrawReason.TIME
                    forfeit_reason = ForfeitReason.TIMEOUT

                # Update remaining time to reflect the timeout (set to 0 if negative)
                if cur_left < 0:
                    remaining[state.current_player_id] = 0
                    state.remaining_time_ms = remaining

                state.last_timestamp_ms = None
                state.winner = winner
                state.draw_reason = reason
                state.forfeit_reason = forfeit_reason
                state.is_finished = True
                event_collector.add(
                    GameFinishedEvent(
                        turn=state.turn,
                        winner=winner,
                        draw_reason=reason,
                        forfeit_reason=forfeit_reason,
                    )
                )
                return
            remaining[state.current_player_id] = cur_left
            state.remaining_time_ms = remaining

    def _apply_move_with_python_chess(self, state: ChessState, move: PlayerMove[ChessMoveData], event_collector: EventCollector[ChessEvent]) -> None:
        """Apply move using python-chess for all chess logic."""
        data = move.data
        chess_board = state.get_chess_board()

        # Capture state before move for analysis
        state_before = state.model_copy(deep=True)

        # Convert our move to python-chess move
        try:
            from_sq = _pychess.parse_square(data.from_square)
            to_sq = _pychess.parse_square(data.to_square)

            if data.promotion:
                promo_map = {"q": _pychess.QUEEN, "r": _pychess.ROOK, "b": _pychess.BISHOP, "n": _pychess.KNIGHT}
                if data.promotion not in promo_map:
                    raise ValueError(f"Invalid promotion piece '{data.promotion}'. Use 'q', 'r', 'b', or 'n'.")
                chess_move = _pychess.Move(from_sq, to_sq, promotion=promo_map[data.promotion])
            else:
                chess_move = _pychess.Move(from_sq, to_sq)
        except Exception as e:
            raise ValueError(f"Invalid move format: {e}") from e

        # Validate move is legal
        if chess_move not in chess_board.legal_moves:
            error_msg = self._diagnose_illegal_move(state, data.from_square, data.to_square, data.promotion)
            raise ValueError(error_msg)

        # Check if it's a capture before applying the move
        is_capture = chess_board.is_capture(chess_move)

        # Get move in SAN notation for analysis BEFORE pushing the move
        move_san = chess_board.san(chess_move)

        # Apply the move using python-chess
        chess_board.push(chess_move)

        # Update our state from the new chess board state
        state.sync_from_chess_board(chess_board)

        # Calculate captured pieces and material advantage
        state.calculate_captured_pieces()

        # Increment turn counter after each move
        state.turn += 1

        # Handle player switching and timing
        next_player = self._other_player_id(state, state.current_player_id)
        state.current_player_id = next_player

        # Update timing
        now_ms = int(time.time() * 1000) if not self.config.disable_timers else None
        remaining = dict(state.remaining_time_ms)
        remaining[next_player] = remaining.get(next_player, 0)
        state.remaining_time_ms = remaining
        state.last_timestamp_ms = now_ms

        # Reset game end flags (they'll be set below if needed)
        state.is_finished = False
        state.winner = None
        state.draw_reason = None

        # Emit move played event
        event_collector.add(
            MovePlayedEvent(
                turn=state.turn,
                player_id=move.player_id,
                from_square=data.from_square,
                to_square=data.to_square,
                promotion=data.promotion,
                is_capture=is_capture,
            )
        )

        # Trigger async move analysis via SQS (fire-and-forget, doesn't block game)
        self._queue_move_analysis(
            state=state,
            state_before=state_before,
            move=move,
            move_san=move_san,
        )

        # Check for game end conditions using python-chess
        self._check_game_end_conditions(state, move.player_id, chess_board, event_collector)

    def _queue_move_analysis(
        self,
        state: ChessState,
        state_before: ChessState,
        move: PlayerMove[ChessMoveData],
        move_san: str,
    ) -> None:
        """Queue move analysis via SQS (fire-and-forget, doesn't block game)."""
        # Queue analysis via SQS with full state objects
        # This is a synchronous call that internally uses asyncio to send the message
        import asyncio

        from game_api import GameType

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Create task to queue the analysis
            _ = asyncio.create_task(
                self.analysis_handler.queue_analysis(
                    game_id=state.game_id,
                    game_type=GameType.CHESS,
                    round_number=state.turn,
                    player_id=move.player_id,
                    move_san=move_san,
                    state_before=state_before,
                    state_after=state,
                )
            )
        except Exception as e:
            # Log but don't fail the game if analysis queueing fails
            from common.utils.utils import get_logger

            logger = get_logger(__name__)
            logger.warning(f"Failed to queue move analysis: {e}")

    def _check_game_end_conditions(self, state: ChessState, last_player_id: PlayerId, chess_board: Any, event_collector: EventCollector[ChessEvent]) -> None:
        """Check for game end conditions using python-chess."""
        # Check for checkmate
        if chess_board.is_checkmate():
            state.is_finished = True
            state.winner = last_player_id  # The player who just moved wins
            event_collector.add(
                GameFinishedEvent(
                    turn=state.turn,
                    winner=last_player_id,
                    draw_reason=None,
                )
            )
            return

        # Check for stalemate
        if chess_board.is_stalemate():
            state.is_finished = True
            state.winner = None
            state.draw_reason = DrawReason.STALEMATE
            event_collector.add(
                GameFinishedEvent(
                    turn=state.turn,
                    winner=None,
                    draw_reason=DrawReason.STALEMATE,
                )
            )
            return

        # Check for insufficient material
        if chess_board.is_insufficient_material():
            state.is_finished = True
            state.winner = None
            state.draw_reason = DrawReason.INSUFFICIENT_MATERIAL
            event_collector.add(
                GameFinishedEvent(
                    turn=state.turn,
                    winner=None,
                    draw_reason=DrawReason.INSUFFICIENT_MATERIAL,
                )
            )
            return

        # Check for 50-move rule
        if chess_board.is_fifty_moves():
            state.is_finished = True
            state.winner = None
            state.draw_reason = DrawReason.FIFTY_MOVES
            event_collector.add(
                GameFinishedEvent(
                    turn=state.turn,
                    winner=None,
                    draw_reason=DrawReason.FIFTY_MOVES,
                )
            )
            return

        # Check for threefold repetition
        if chess_board.is_repetition(3):
            state.is_finished = True
            state.winner = None
            state.draw_reason = DrawReason.THREEFOLD_REPETITION
            event_collector.add(
                GameFinishedEvent(
                    turn=state.turn,
                    winner=None,
                    draw_reason=DrawReason.THREEFOLD_REPETITION,
                )
            )
            return

    @override
    def calc_possible_moves(self, state: ChessState, player_id: PlayerId) -> ChessPossibleMoves | None:
        """Calculate all possible legal moves for the current player using python-chess.

        Only returns moves for the active player (current_player_id).
        """
        # Only calculate moves for the current player
        if player_id != state.current_player_id:
            return None

        try:
            # Get the internal chess board
            chess_board = state.get_chess_board()

            # Get all legal moves from python-chess
            legal_moves = list(chess_board.legal_moves)

            # Convert python-chess moves to ChessPossibleMove objects
            possible_moves: list[ChessPossibleMove] = []

            for move in legal_moves:
                # Convert square indices to algebraic notation
                from_square = _pychess.square_name(move.from_square)
                to_square = _pychess.square_name(move.to_square)

                # Get the piece type at the from_square
                piece_at_square = chess_board.piece_at(move.from_square)
                if piece_at_square is None:
                    continue  # Skip if no piece (shouldn't happen for legal moves)

                # Map python-chess piece type to our PieceType enum
                piece_type_map = {
                    _pychess.PAWN: PieceType.PAWN,
                    _pychess.KNIGHT: PieceType.KNIGHT,
                    _pychess.BISHOP: PieceType.BISHOP,
                    _pychess.ROOK: PieceType.ROOK,
                    _pychess.QUEEN: PieceType.QUEEN,
                    _pychess.KING: PieceType.KING,
                }
                piece_type = piece_type_map[piece_at_square.piece_type]

                # Handle promotion moves
                promotion: list[str] | None = None
                if move.promotion is not None:
                    # Map python-chess promotion constants to our notation
                    promo_map = {_pychess.QUEEN: ["q"], _pychess.ROOK: ["r"], _pychess.BISHOP: ["b"], _pychess.KNIGHT: ["n"]}
                    promotion = promo_map.get(move.promotion, [])

                # Check if this move results in check
                # We need to make the move on a copy of the board to see if it results in check
                temp_board = chess_board.copy()
                temp_board.push(move)
                is_check = temp_board.is_check()

                possible_moves.append(
                    ChessPossibleMove(
                        from_square=from_square,
                        to_square=to_square,
                        piece=piece_type,
                        is_check=is_check,
                        promotion=cast(list[Literal["q", "r", "b", "n"]] | None, promotion),
                    )
                )

            return ChessPossibleMoves(possible_moves=possible_moves)

        except Exception:
            # If anything goes wrong, return None to maintain backward compatibility
            return None

    @override
    def get_player_view(self, state: ChessState, player_id: PlayerId, events: list[ChessEvent]) -> ChessStateView:
        # Convert events to player view events
        player_view_events: list[ChessPlayerViewEvent] = [
            view_event for event in events if (view_event := self._convert_to_player_view_event(event, player_id)) is not None
        ]

        # Convert board to map representation for the player view
        board_map = board_to_map(state.board)

        return ChessStateView(
            board=board_map,
            side_to_move=state.side_to_move,
            castling_rights=state.castling_rights,
            en_passant_square=state.en_passant_square,
            halfmove_clock=state.halfmove_clock,
            fullmove_number=state.fullmove_number,
            players=state.players,
            remaining_time_ms=state.remaining_time_ms,
            last_timestamp_ms=state.last_timestamp_ms,
            captured_pieces=state.captured_pieces,
            material_advantage=state.material_advantage,
            is_finished=state.is_finished,
            winner=state.winner,
            draw_reason=state.draw_reason,
            events=player_view_events,
        )

    def _convert_to_player_view_event(self, event: ChessEvent, viewer_id: PlayerId) -> ChessPlayerViewEvent | None:
        match event:
            case GameInitializedEvent():
                return None

            case PlayerJoinedEvent() as joined_event:
                return PlayerJoinedPlayerViewEvent(
                    timestamp=joined_event.timestamp,
                    turn=joined_event.turn,
                    player_id=joined_event.player_id,
                    name=joined_event.name,
                )

            case PlayerLeftEvent() as left_event:
                return PlayerLeftPlayerViewEvent(
                    timestamp=left_event.timestamp,
                    turn=left_event.turn,
                    player_id=left_event.player_id,
                    reason=left_event.reason,
                )

            case MovePlayedEvent() as move_event:
                return MovePlayedPlayerViewEvent(
                    timestamp=move_event.timestamp,
                    turn=move_event.turn,
                    player_id=move_event.player_id,
                    from_square=move_event.from_square,
                    to_square=move_event.to_square,
                    promotion=move_event.promotion,
                    is_capture=move_event.is_capture,
                )

            case CheckEvent() as check_event:
                return CheckPlayerViewEvent(
                    timestamp=check_event.timestamp,
                    turn=check_event.turn,
                    side_in_check=check_event.side_in_check,
                )

            case CheckmateEvent() as checkmate_event:
                return CheckmatePlayerViewEvent(
                    timestamp=checkmate_event.timestamp,
                    turn=checkmate_event.turn,
                    winner=checkmate_event.winner,
                )

            case StalemateEvent() as stalemate_event:
                return StalematePlayerViewEvent(
                    timestamp=stalemate_event.timestamp,
                    turn=stalemate_event.turn,
                    reason=stalemate_event.reason,
                )

            case GameFinishedEvent() as finished_event:
                return GameFinishedPlayerViewEvent(
                    timestamp=finished_event.timestamp,
                    turn=finished_event.turn,
                    winner=finished_event.winner,
                    draw_reason=finished_event.draw_reason,
                )

            case AgentReasoningEvent() as reasoning_event:
                # Only show reasoning events to the player who made them
                if reasoning_event.player_id != viewer_id:
                    return None
                return AgentReasoningPlayerViewEvent(
                    timestamp=reasoning_event.timestamp,
                    turn=reasoning_event.turn,
                    player_id=reasoning_event.player_id,
                    reasoning=reasoning_event.reasoning,
                )

            case ChatMessageEvent() as chat_event:
                # Show all chat messages to all players
                return ChatMessagePlayerViewEvent(
                    timestamp=chat_event.timestamp,
                    turn=chat_event.turn,
                    player_id=chat_event.player_id,
                    message=chat_event.message,
                )

            case MoveAnalysisEvent():
                # Filter out analysis events - they shouldn't be visible to agents
                return None

            case AgentForfeitEvent() as forfeit_event:
                # Show agent forfeit events to all players
                return AgentForfeitPlayerViewEvent(
                    timestamp=forfeit_event.timestamp,
                    turn=forfeit_event.turn,
                    player_id=forfeit_event.player_id,
                    reason=forfeit_event.reason,
                )

    @override
    def error_fallback_move(self, state: ChessState, event_collector: EventCollector[ChessEvent], player_id: PlayerId) -> ChessMoveData:
        if state.current_player_id != player_id:
            raise ValueError("Not this player's turn")

        try:
            # Use the internal chess board for better performance
            chess_board = state.get_chess_board()
            legal_moves = list(chess_board.legal_moves)
            if not legal_moves:
                raise ValueError("No legal moves available")

            # Use the first legal move as fallback
            move = legal_moves[0]
            from_square = _pychess.square_name(move.from_square)
            to_square = _pychess.square_name(move.to_square)

            # Handle promotion
            promotion = None
            if move.promotion:
                promo_map = {_pychess.QUEEN: "q", _pychess.ROOK: "r", _pychess.BISHOP: "b", _pychess.KNIGHT: "n"}
                promotion_str = promo_map.get(move.promotion)
                if promotion_str in ("q", "r", "b", "n"):
                    promotion = promotion_str

            return ChessMoveData(from_square=from_square, to_square=to_square, promotion=promotion)
        except Exception as e:
            raise ValueError(f"Could not generate fallback move: {e}") from e

    @classmethod
    @override
    def get_state_generation_system_prompt(cls) -> str:
        """System prompt for chess state generation (with hard constraints)."""
        return (
            "You will generate a valid ChessStateView JSON. "
            "Follow the provided JSON Schema exactly (keys are snake_case). "
            "HARD CONSTRAINTS: Exactly one king per color; kings must not be adjacent; "
            "the non-moving side's king must NOT be in check; the side_to_move's king MAY be in check; "
            "no pawns on rank 1 or 8; en_passant_square null or a valid square on rank 3 or 6; "
            "castling_rights must be consistent with piece placement (king/rooks on starting squares if rights are true). "
            "Castling: if rights are inconsistent with placement, DISABLE the rights (set to false) rather than moving pieces. "
            "Avoid draw states: do NOT produce stalemate or insufficient-mating-material positions (exclude K vs K, K+B vs K, K+N vs K, K+NN vs K). "
            "Avoid swapped orientation: do not place most white pieces on ranks 7-8 and most black pieces on ranks 1-2. "
            "Before answering, internally verify these constraints and correct any violations. "
            "Only return the JSON object, with no extra text."
        )

    @classmethod
    @override
    def create_state_generation_user_prompt(cls, description: str) -> str:
        """User prompt builder for chess state generation (perfect information)."""
        return f"""Generate a realistic chess game state (perfect information) based on this description: {description}

CRITICAL BOARD ARRAY INDEXING:
The board is an 8x8 array where:
- board[0] = rank 8 (BLACK's back rank: a8-h8, where BLACK pieces start)
- board[1] = rank 7 (BLACK's pawn rank)
- board[2] = rank 6
- board[3] = rank 5
- board[4] = rank 4
- board[5] = rank 3
- board[6] = rank 2 (WHITE's pawn rank)
- board[7] = rank 1 (WHITE's back rank: a1-h1, where WHITE pieces start)

Within each rank, files go a-h (left to right): board[rank][0]=a, board[rank][1]=b, ..., board[rank][7]=h

STANDARD STARTING POSITION EXAMPLE:
- board[0] = [Rook(black), Knight(black), Bishop(black), Queen(black), King(black), Bishop(black), Knight(black), Rook(black)]  // rank 8
- board[1] = [Pawn(black), Pawn(black), ..., Pawn(black)]  // rank 7
- board[6] = [Pawn(white), Pawn(white), ..., Pawn(white)]  // rank 2
- board[7] = [Rook(white), Knight(white), Bishop(white), Queen(white), King(white), Bishop(white), Knight(white), Rook(white)]  // rank 1

REQUIREMENTS:
- Represent the board as an 8x8 array (rank 8..1 top to bottom); each square is either null or an object with: {{ "type": "king|queen|rook|bishop|knight|pawn", "color": "white|black" }}.
- Include: side_to_move, castling_rights (white_kingside, white_queenside, black_kingside, black_queenside), en_passant_square (or null),
  halfmove_clock (>= 0), fullmove_number (>= 1), is_finished (boolean), winner (or null), draw_reason (or null).
- Clocks are optional: remaining_time_ms may be an empty object and last_timestamp_ms may be null.
- Avoid swapped orientation: do NOT place most white pieces on ranks 7-8 while most black pieces are on ranks 1-2.

- HARD CONSTRAINTS: Exactly one king per color; kings must not be adjacent; non-moving side's king must not be in check; side_to_move's king may be in check; forbid both kings in check; pawns not on rank 1 or 8; en_passant_square is null or a valid square on rank 3 or 6; castling rights must match king/rook starting placement.

- Avoid draw states: do NOT return stalemate or insufficient-mating-material positions (exclude K vs K, K+B vs K, K+N vs K, K+NN vs K).
- Perform an internal legality self-check and correct violations before returning the JSON.
- Only return the JSON object, no extra text.
"""

    @classmethod
    @override
    def get_state_generation_examples(cls) -> list[str]:
        return [
            "Opening: Standard initial position, white to move, classical time control.",
            "Middlegame: White to move, no side is in check; white isolated d-pawn; both sides can still castle.",
            "Tactical: Black to move with a back-rank motif coming; ensure no king is currently in check; kings well separated.",
            "Endgame: K+P vs K; white to move; kings not adjacent; no side in check; specify exact squares for kings and the pawn.",
            "Endgame: K+B+N vs K; black to move; kings not adjacent; no side in check.",
            "Castling rights: White may castle kingside only (king on e1, rook on h1); black has no castling rights.",
            "En passant setup: After a legal double pawn push by black last move, set en_passant_square to e3 (or similar on rank 3); now it's white to move.",
            "Balanced middlegame: opposite-side castling not allowed; include realistic piece placement and clocks.",
        ]

    @classmethod
    @override
    def validate_generated_state(cls, state_data: dict[str, Any]) -> ChessStateView:
        """Schema-validate and convert generated state data to ChessStateView.

        IMPORTANT: This only performs Pydantic model validation/normalization.
        Domain/legality checks are performed in validate_test_json().
        """
        try:
            view = ChessStateView.model_validate(state_data)
            return view
        except Exception as e:
            raise ValueError(f"Generated chess state is invalid: {e}") from e

    @classmethod
    @override
    def validate_test_json(cls, state_view: ChessStateView) -> ChessStateView:
        """Environment-specific legality checks for Chess test JSON using python-chess.

        Uses python-chess to validate the position is legal and makes sense.
        """
        try:
            # Convert the state view to a python-chess board for validation
            chess_board = cls._python_chess_board_from_state_view(state_view)

            # Basic validation - python-chess will raise an exception if the position is invalid
            # This checks for:
            # - Exactly one king per color
            # - Kings not adjacent
            # - No pawns on rank 1 or 8
            # - Valid piece placement
            # - Consistent castling rights
            # - Valid en passant square

            # Additional check: ensure the non-moving side is not in check
            # (the side that just moved cannot leave the opponent in check)
            if chess_board.is_check():
                # If it's white's turn and white is in check, that's fine (white needs to get out of check)
                # If it's white's turn and black is in check, that's illegal (black should have been in check before white's last move)
                current_side_in_check = chess_board.turn
                if not current_side_in_check:  # If the current side to move is NOT in check, but someone is in check, it's invalid
                    raise ValueError("The non-moving side cannot be in check")

            # Check for obviously invalid positions
            if chess_board.is_insufficient_material():
                # Allow insufficient material positions for testing purposes
                pass

            return state_view

        except Exception as e:
            raise ValueError(f"Invalid chess position: {e}") from e

    @classmethod
    def _python_chess_board_from_state_view(cls, state_view: ChessStateView) -> Any:
        """Convert a ChessStateView to a python-chess Board object for validation."""
        # Convert board map to 2D array for FEN generation
        board_array = map_to_board(state_view.board)

        # Build FEN string from state view
        fen_parts: list[str] = []
        board_fen: list[str] = []

        # 1. Piece placement (from rank 8 to rank 1)
        for rank_idx in range(8):  # Our board[0] = rank 8, board[7] = rank 1
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
                    # Convert our piece to FEN notation
                    piece_char = piece.type.value[0].lower()  # k, q, r, b, n, p
                    if piece.type == PieceType.KNIGHT:
                        piece_char = "n"
                    if piece.color == Color.WHITE:
                        piece_char = piece_char.upper()
                    rank_str += piece_char
            if empty_count > 0:
                rank_str += str(empty_count)
            board_fen.append(rank_str)
        fen_parts.append("/".join(board_fen))

        # 2. Active color
        fen_parts.append("w" if state_view.side_to_move == Color.WHITE else "b")

        # 3. Castling rights
        castling = ""
        if state_view.castling_rights.white_kingside:
            castling += "K"
        if state_view.castling_rights.white_queenside:
            castling += "Q"
        if state_view.castling_rights.black_kingside:
            castling += "k"
        if state_view.castling_rights.black_queenside:
            castling += "q"
        fen_parts.append(castling if castling else "-")

        # 4. En passant square
        fen_parts.append(state_view.en_passant_square if state_view.en_passant_square else "-")

        # 5. Halfmove clock
        fen_parts.append(str(state_view.halfmove_clock))

        # 6. Fullmove number
        fen_parts.append(str(state_view.fullmove_number))

        fen = " ".join(fen_parts)
        return _pychess.Board(fen)

    @classmethod
    def state_view_from_fen(cls, fen: str) -> ChessStateView:
        """Build a ChessStateView from a FEN string using python-chess.

        Note: Clocks are left empty; last_timestamp_ms is None; is_finished is false.
        """
        try:
            board_obj = _pychess.Board(fen)
        except Exception as e:
            raise ValueError(f"Invalid FEN: {e}") from e

        return cls._state_view_from_python_chess_board(board_obj)

    @classmethod
    def state_view_from_moves(cls, moves: str) -> ChessStateView:
        """Build a ChessStateView from a SAN/PGN-like move list.

        Tokens can include move numbers and result markers; they will be ignored.
        """
        board_obj = _pychess.Board()
        # Normalize whitespace and split tokens
        tokens = moves.replace("\n", " ").replace("\r", " ").split()
        for tok in tokens:
            # Skip move numbers (like 1., 23.) and results
            if tok.endswith("."):
                continue
            if tok in {"1-0", "0-1", "1/2-1/2", "*"}:
                continue
            clean = tok.strip()
            try:
                _ = board_obj.push_san(clean)
            except Exception as e:
                raise ValueError(f"Invalid move token '{tok}': {e}") from e

        return cls._state_view_from_python_chess_board(board_obj)

    @classmethod
    def _state_view_from_python_chess_board(cls, board_obj: _pychess.Board) -> ChessStateView:
        # Build board map directly from the chess board
        board: ChessBoardMap = {}

        for rank in range(8, 0, -1):  # 8..1
            for file_char in ("a", "b", "c", "d", "e", "f", "g", "h"):
                sq = _pychess.parse_square(f"{file_char}{rank}")
                p = board_obj.piece_at(sq)
                if p is not None:
                    color = Color.WHITE if p.color == _pychess.WHITE else Color.BLACK
                    pt_map = {
                        _pychess.PAWN: PieceType.PAWN,
                        _pychess.KNIGHT: PieceType.KNIGHT,
                        _pychess.BISHOP: PieceType.BISHOP,
                        _pychess.ROOK: PieceType.ROOK,
                        _pychess.QUEEN: PieceType.QUEEN,
                        _pychess.KING: PieceType.KING,
                    }
                    board[f"{file_char}{rank}"] = ChessPiece(type=pt_map[p.piece_type], color=color)

        cr = CastlingRights(
            white_kingside=board_obj.has_kingside_castling_rights(_pychess.WHITE),
            white_queenside=board_obj.has_queenside_castling_rights(_pychess.WHITE),
            black_kingside=board_obj.has_kingside_castling_rights(_pychess.BLACK),
            black_queenside=board_obj.has_queenside_castling_rights(_pychess.BLACK),
        )

        ep_sq: str | None
        ep_sq = _pychess.square_name(board_obj.ep_square) if board_obj.ep_square is not None and board_obj.has_legal_en_passant() else None

        side_to_move = Color.WHITE if board_obj.turn == _pychess.WHITE else Color.BLACK

        view = ChessStateView(
            board=board,
            side_to_move=side_to_move,
            castling_rights=cr,
            en_passant_square=ep_sq,
            halfmove_clock=int(getattr(board_obj, "halfmove_clock", 0)),
            fullmove_number=int(getattr(board_obj, "fullmove_number", 1)),
            players=[],  # Empty players list for FEN/moves-based views
            remaining_time_ms={},
            last_timestamp_ms=None,
            is_finished=False,
            winner=None,
            draw_reason=None,
        )
        # Reuse existing validation to ensure legality/sanity beyond schema
        return cls.validate_test_json(view)

    @override
    @classmethod
    def extract_game_result(cls, state: ChessState) -> GameResult:
        """Extract game result information from chess state."""
        return GameResult(
            winner_id=state.winner,
            winners_ids=[],
            draw_reason=state.draw_reason,
            final_scores=None,
        )

    @override
    def on_player_left(
        self,
        state: ChessState,
        leaving_player_id: PlayerId,
        event_collector: EventCollector[ChessEvent],
    ) -> FinishDecision:
        """Handle a player leaving the chess game.

        Emits a PlayerLeftEvent and determines whether the game should finish.
        For chess, if a player leaves during an in-progress game, the other player wins.

        Args:
            state: Current chess game state
            leaving_player_id: ID of the player who is leaving
            event_collector: Collector for events to emit

        Returns:
            FinishDecision indicating whether game should continue, finish, or be cancelled
        """
        # Emit PlayerLeftEvent
        event = PlayerLeftEvent(
            player_id=leaving_player_id,
            reason="user_initiated",
            turn=state.turn,
        )
        event_collector.add(event)

        # Determine finish decision based on remaining players
        remaining_players = [p for p in state.players if p != leaving_player_id]

        if len(remaining_players) == 0:
            # No players left - cancel the game
            return FinishDecision.CANCEL
        elif len(remaining_players) < self.config.min_players:
            # Below minimum players (for chess, this means < 2) - finish with remaining player as winner
            return FinishDecision.FINISH
        else:
            # Still have enough players - continue (shouldn't happen for chess, but handle gracefully)
            return FinishDecision.CONTINUE

    @override
    def finish_due_to_forfeit(
        self,
        state: ChessState,
        remaining_player_ids: list[PlayerId],
        event_collector: EventCollector[ChessEvent],
    ) -> None:
        """Finish the chess game by declaring the remaining player as winner.

        Modifies state in place to mark game as finished with the remaining player as winner.
        This is a win by forfeit, NOT a draw - only the winner field is set.

        Args:
            state: Chess game state to modify
            remaining_player_ids: IDs of players still in the game (should be 1 for chess)
            event_collector: Collector for any final events
        """
        from chess_game.chess_api import ForfeitReason

        logger = get_logger()
        logger.info(
            "Finishing chess game due to forfeit",
            game_id=str(state.game_id),
            all_players=str(state.players),
            remaining_player_ids=str(remaining_player_ids),
            current_player_id=str(state.current_player_id),
        )

        # Mark game as finished
        state.is_finished = True

        # Set winner to the remaining player (if any)
        if remaining_player_ids:
            state.winner = remaining_player_ids[0]
            logger.info(
                "Winner set to remaining player",
                game_id=str(state.game_id),
                winner=str(state.winner),
            )
        else:
            state.winner = None
            logger.warning(
                "No remaining players - no winner set",
                game_id=str(state.game_id),
            )

        # Set forfeit reason - player resigned/left the game
        state.forfeit_reason = ForfeitReason.RESIGNATION

        # Do NOT set draw_reason - forfeit is a win/loss, not a draw
        # draw_reason should only be set for actual draws (stalemate, insufficient material, etc.)

        # Emit GameFinishedEvent to record the forfeit win
        event_collector.add(
            GameFinishedEvent(
                turn=state.turn,
                winner=state.winner,
                draw_reason=None,  # Forfeit is not a draw
                forfeit_reason=ForfeitReason.RESIGNATION,
            )
        )

    @classmethod
    @override
    def get_tool_creation_context(cls) -> Any:
        """Get context for tool creation in Chess environment.

        Returns:
            ToolCreationContext specialized for Chess.
        """
        from common.agents.models import ToolCreationContext, ToolExample

        return ToolCreationContext[ChessStateView, ChessPossibleMoves, ChessMoveData](
            environment=GameType.CHESS,
            state_schema=ChessStateView.model_json_schema(),
            possible_moves_schema=ChessPossibleMoves.model_json_schema(),
            move_data_schema=ChessMoveData.model_json_schema(),
            constraints=[
                "Tools must validate move legality according to chess rules",
                "Tools must handle all special moves: castling, en passant, pawn promotion",
                "Tools must consider time control if applicable",
                "Tools must respect check and checkmate conditions",
                "Tools cannot modify game state, only analyze it",
            ],
            best_practices=[
                "Use material count for basic position evaluation",
                "Consider piece activity and mobility",
                "Evaluate king safety and pawn structure",
                "Check for tactical patterns (pins, forks, skewers)",
                "Consider positional factors (center control, development)",
                "Account for endgame vs middlegame dynamics",
            ],
            example_tools=[
                ToolExample(
                    name="material_evaluator",
                    display_name="Material Evaluator",
                    description="Evaluate material balance on the board",
                    explanation="Calculates material advantage using standard piece values (pawn=1, knight=3, bishop=3, rook=5, queen=9)",
                    code='''def lambda_handler(event, context):
    """Evaluate material balance."""
    state = event["state"]
    # Use the board coordinate map for piece lookup
    board = state["board"]

    # Piece values
    piece_values = {
        "pawn": 1, "knight": 3, "bishop": 3, "rook": 5, "queen": 9, "king": 0
    }

    # Calculate material
    material_balance = 0
    white_material = 0
    black_material = 0

    for coord, piece in board.items():
        if "type" in piece and "color" in piece:
            piece_type = piece["type"]
            piece_color = piece["color"]
            value = piece_values.get(piece_type, 0)

            if piece_color == "white":
                white_material += value
                material_balance += value
            elif piece_color == "black":
                black_material += value
                material_balance -= value

    return {
        "material_balance": material_balance,
        "white_material": white_material,
        "black_material": black_material,
        "advantage": "White" if material_balance > 0 else "Black" if material_balance < 0 else "Equal",
        "message": f"Material: White {white_material} - Black {black_material} (Balance: {material_balance:+d})"
    }
''',
                ),
                ToolExample(
                    name="center_control_analyzer",
                    display_name="Center Control Analyzer",
                    description="Analyze control of the center squares (d4, d5, e4, e5)",
                    explanation="Evaluates which side controls the critical center squares, important for opening and middlegame strategy",
                    code='''def lambda_handler(event, context):
    """Analyze center control."""
    state = event["state"]
    # Use the board coordinate map for piece lookup
    board = state["board"]

    # Center squares
    center_squares = ["d4", "d5", "e4", "e5"]

    white_control = 0
    black_control = 0

    for square in center_squares:
        piece = board.get(square)
        if piece and "type" in piece and "color" in piece:
            if piece["color"] == "white":
                white_control += 1
            elif piece["color"] == "black":
                black_control += 1

    return {
        "white_control": white_control,
        "black_control": black_control,
        "center_advantage": "White" if white_control > black_control else "Black" if black_control > white_control else "Equal",
        "message": f"Center control: White {white_control}/4, Black {black_control}/4"
    }
''',
                ),
            ],
            tool_creation_guidance="""
Chess Tool Creation Guidelines:

**Input Structure:**
- Tools receive a `state` dict containing the ChessStateView
- Board is a coordinate map where keys are squares like "a1", "e4", etc.
  Example: {"a1": {"type": "rook", "color": "white"}, "e4": {"type": "pawn", "color": "white"}}
- Each piece is an object with "type" and "color" keys
- Piece format: {"type": "pawn"|"knight"|"bishop"|"rook"|"queen"|"king", "color": "white"|"black"}
- Side to move available in `state["side_to_move"]` ("white" or "black")

**Example Test JSON Format:**
```json
{
  "state": {
    "board": {
      "a8": {"type": "rook", "color": "black"}, "b8": {"type": "knight", "color": "black"},
      "c8": {"type": "bishop", "color": "black"}, "d8": {"type": "queen", "color": "black"},
      "e8": {"type": "king", "color": "black"}, "f8": {"type": "bishop", "color": "black"},
      "g8": {"type": "knight", "color": "black"}, "h8": {"type": "rook", "color": "black"},
      "a7": {"type": "pawn", "color": "black"}, "b7": {"type": "pawn", "color": "black"},
      "c7": {"type": "pawn", "color": "black"}, "d7": {"type": "pawn", "color": "black"},
      "e7": {"type": "pawn", "color": "black"}, "f7": {"type": "pawn", "color": "black"},
      "g7": {"type": "pawn", "color": "black"}, "h7": {"type": "pawn", "color": "black"},
      "e4": {"type": "pawn", "color": "white"}, "d4": {"type": "pawn", "color": "white"},
      "a1": {"type": "rook", "color": "white"}, "b1": {"type": "knight", "color": "white"},
      "c1": {"type": "bishop", "color": "white"}, "d1": {"type": "queen", "color": "white"},
      "e1": {"type": "king", "color": "white"}, "f1": {"type": "bishop", "color": "white"},
      "g1": {"type": "knight", "color": "white"}, "h1": {"type": "rook", "color": "white"}
    },
    "side_to_move": "white",
    "castling_rights": {"whiteKingside": true, "whiteQueenside": true, "blackKingside": true, "blackQueenside": true},
    "en_passant_square": null,
    "halfmove_clock": 0,
    "fullmove_number": 5
  }
}
```

**Common Tool Types:**
1. **Material Evaluators**: Calculate material advantage
2. **Position Analyzers**: Evaluate positional factors
3. **Tactical Finders**: Detect tactical patterns
4. **Move Suggesters**: Recommend candidate moves
5. **Opening Analyzers**: Identify opening variations

**Key Considerations:**
- Use the board coordinate map for easy piece lookup by square coordinates
- Special moves: castling rights, en passant square
- Game phase matters (opening, middlegame, endgame)
- Time control affects decision making

**Return Format:**
Tools should return a dictionary with:
- Calculated values (material, position score, etc.)
- Explanatory message
- Any relevant warnings or tactical alerts
""",
        )
