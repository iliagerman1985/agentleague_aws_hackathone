from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

import chess as _pychess
from game_api import (
    BaseAgentDecision,
    BaseGameConfig,
    BaseGameEvent,
    BaseGameState,
    BaseGameStateView,
    BasePlayerMoveData,
    BasePlayerPossibleMoves,
    BasePlayerViewEvent,
    ChatMessageMixin,
    GameId,
    GameType,
    ReasoningEventMixin,
)
from pydantic import Field

from common.ids import AgentVersionId, PlayerId
from common.types import AgentReasoning
from common.utils.json_model import JsonModel

# ----------------------------------
# Core chess domain types
# ----------------------------------


class PieceType(StrEnum):
    KING = "king"
    QUEEN = "queen"
    ROOK = "rook"
    BISHOP = "bishop"
    KNIGHT = "knight"
    PAWN = "pawn"


class Color(StrEnum):
    WHITE = "white"
    BLACK = "black"


class DrawReason(StrEnum):
    """Reasons for a draw in chess."""

    STALEMATE = "stalemate"
    FIFTY_MOVES = "fifty_moves"
    THREEFOLD_REPETITION = "threefold_repetition"
    INSUFFICIENT_MATERIAL = "insufficient_material"
    AGREEMENT = "agreement"
    FORFEIT = "forfeit"
    TIME = "time"
    TIMEOUT_INSUFFICIENT_MATERIAL = "timeout_insufficient_material"


class ForfeitReason(StrEnum):
    """Reasons for a forfeit/resignation in chess."""

    RESIGNATION = "resignation"  # Player voluntarily resigned
    TIMEOUT = "timeout"  # Player ran out of time
    ABANDONMENT = "abandonment"  # Player left/disconnected
    FAILED_TO_MOVE = "failed_to_move"  # Agent failed to produce valid move


class ChessPiece(JsonModel):
    type: PieceType = Field(..., description="Type of the piece")
    color: Color = Field(..., description="Color of the piece")


class CastlingRights(JsonModel):
    white_kingside: bool = Field(default=True)
    white_queenside: bool = Field(default=True)
    black_kingside: bool = Field(default=True)
    black_queenside: bool = Field(default=True)


# ----------------------------------
# Config
# ----------------------------------


class ChessTimeControl(StrEnum):
    BLITZ = "blitz"  # 10 minutes per player
    LONG = "long"  # 20 minutes per player


class ChessPlaygroundOpponent(StrEnum):
    SELF = "self"
    BRAIN = "brain"


class ChessSide(StrEnum):
    """Side selection for chess playground."""

    WHITE = "white"
    BLACK = "black"


class ChessConfig(BaseGameConfig):
    """Configuration for Chess."""

    env: GameType = GameType.CHESS
    min_players: int = Field(default=2, ge=2)
    max_players: int = Field(default=2, ge=2)
    time_control: ChessTimeControl = Field(default=ChessTimeControl.LONG, description="Game time control")
    disable_timers: bool = Field(default=False, description="Disable chess clocks (e.g., for playground)")
    playground_opponent: ChessPlaygroundOpponent | None = Field(
        default=None,
        description="Opponent configuration for playground sessions",
    )
    user_side: ChessSide = Field(
        default=ChessSide.WHITE,
        description="Which side the user's agent plays (white or black) in playground mode",
    )


# ----------------------------------
# State and View (perfect information)
# ----------------------------------


class ChessState(BaseGameState):
    env: GameType = GameType.CHESS
    # 8x8 board: ranks 8..1 top->bottom in UI; files a..h left->right.
    # Represented as list of 8 ranks, each rank is a list of 8 squares.
    # Each square holds a ChessPiece or None.
    board: list[list[ChessPiece | None]] = Field(..., description="8x8 board matrix")

    side_to_move: Color = Field(default=Color.WHITE, description="Side to move next")
    castling_rights: CastlingRights = Field(default_factory=CastlingRights, description="Castling rights")
    en_passant_square: str | None = Field(default=None, description="Square available for en passant (e.g., 'e3')")
    halfmove_clock: int = Field(default=0, ge=0, description="Halfmove clock for 50-move rule")
    fullmove_number: int = Field(default=1, ge=1, description="Fullmove number (incremented after Black's move)")
    players: list[PlayerId] = Field(default_factory=list, description="List of player IDs in the game (max 2 for chess)")

    # Clocks
    remaining_time_ms: dict[PlayerId, int] = Field(default_factory=dict, description="Per-player remaining time in ms")
    last_timestamp_ms: int | None = Field(default=None, description="Epoch ms when active player's clock last started")

    # Captured pieces tracking
    captured_pieces: dict[Color, list[PieceType]] = Field(
        default_factory=lambda: {Color.WHITE: [], Color.BLACK: []},
        description="Pieces captured by each color (white captures black pieces, black captures white pieces)",
    )
    material_advantage: int = Field(default=0, description="Material advantage for white (positive = white ahead, negative = black ahead)")

    # Optional game resolution fields
    winner: PlayerId | None = Field(default=None, description="Winner player id (if any)")
    draw_reason: DrawReason | None = Field(default=None, description="Reason for draw (stalemate, 50-move rule, repetition, etc.)")
    forfeit_reason: ForfeitReason | None = Field(default=None, description="Reason for forfeit/resignation (if game ended by forfeit)")

    # Internal python-chess Board object (excluded from serialization/database)
    chess_board_internal: Any | None = Field(default=None, exclude=True, description="Internal python-chess Board object")  # Actually _pychess.Board

    def get_chess_board(self) -> _pychess.Board:
        """Get or create the python-chess Board object from current state."""
        if self.chess_board_internal is None:
            self.chess_board_internal = self._build_chess_board_from_state()
        return self.chess_board_internal

    def sync_from_chess_board(self, chess_board: _pychess.Board) -> None:
        """Update our state fields from the python-chess Board."""
        self.chess_board_internal = chess_board
        self._update_fields_from_chess_board(chess_board)

    def _build_chess_board_from_state(self) -> _pychess.Board:
        """Build a python-chess Board from our current state."""
        # Build FEN string from our state
        fen_parts: list[str] = []

        # 1. Piece placement (from rank 8 to rank 1)
        board_fen: list[str] = []
        for rank_idx in range(8):  # Our board[0] = rank 8, board[7] = rank 1
            rank_str = ""
            empty_count = 0
            for file_idx in range(8):
                piece = self.board[rank_idx][file_idx]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        rank_str += str(empty_count)
                        empty_count = 0
                    # Convert our piece to FEN notation
                    # k, q, r, b, n, p
                    piece_char = piece.type.value[0].lower()
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
        fen_parts.append("w" if self.side_to_move == Color.WHITE else "b")

        # 3. Castling rights
        castling = ""
        if self.castling_rights.white_kingside:
            castling += "K"
        if self.castling_rights.white_queenside:
            castling += "Q"
        if self.castling_rights.black_kingside:
            castling += "k"
        if self.castling_rights.black_queenside:
            castling += "q"
        fen_parts.append(castling if castling else "-")

        # 4. En passant square
        fen_parts.append(self.en_passant_square if self.en_passant_square else "-")

        # 5. Halfmove clock
        fen_parts.append(str(self.halfmove_clock))

        # 6. Fullmove number
        fen_parts.append(str(self.fullmove_number))

        fen = " ".join(fen_parts)
        return _pychess.Board(fen)

    def _update_fields_from_chess_board(self, chess_board: _pychess.Board) -> None:
        """Update our state fields from the python-chess Board."""
        # Update board representation
        board: list[list[ChessPiece | None]] = []
        for rank in range(8, 0, -1):  # 8..1
            row: list[ChessPiece | None] = []
            for file_char in ("a", "b", "c", "d", "e", "f", "g", "h"):
                sq = _pychess.parse_square(f"{file_char}{rank}")
                p = chess_board.piece_at(sq)
                if p is None:
                    row.append(None)
                else:
                    color = Color.WHITE if p.color == _pychess.WHITE else Color.BLACK
                    pt_map = {
                        _pychess.PAWN: PieceType.PAWN,
                        _pychess.KNIGHT: PieceType.KNIGHT,
                        _pychess.BISHOP: PieceType.BISHOP,
                        _pychess.ROOK: PieceType.ROOK,
                        _pychess.QUEEN: PieceType.QUEEN,
                        _pychess.KING: PieceType.KING,
                    }
                    piece_type = pt_map[p.piece_type]
                    row.append(ChessPiece(type=piece_type, color=color))
            board.append(row)
        self.board = board

        # Update other fields
        self.side_to_move = Color.WHITE if chess_board.turn == _pychess.WHITE else Color.BLACK

        # Castling rights
        self.castling_rights = CastlingRights(
            white_kingside=chess_board.has_kingside_castling_rights(_pychess.WHITE),
            white_queenside=chess_board.has_queenside_castling_rights(_pychess.WHITE),
            black_kingside=chess_board.has_kingside_castling_rights(_pychess.BLACK),
            black_queenside=chess_board.has_queenside_castling_rights(_pychess.BLACK),
        )

        # En passant square
        if chess_board.ep_square is not None and chess_board.has_legal_en_passant():
            self.en_passant_square = _pychess.square_name(chess_board.ep_square)
        else:
            self.en_passant_square = None

        # Move counters
        self.halfmove_clock = chess_board.halfmove_clock
        self.fullmove_number = chess_board.fullmove_number

    def calculate_captured_pieces(self) -> None:
        """Calculate captured pieces and material advantage based on current board state."""
        # Starting material count for each piece type
        starting_counts = {
            PieceType.PAWN: 8,
            PieceType.ROOK: 2,
            PieceType.KNIGHT: 2,
            PieceType.BISHOP: 2,
            PieceType.QUEEN: 1,
            PieceType.KING: 1,
        }

        # Piece values for material calculation
        piece_values = {
            PieceType.PAWN: 1,
            PieceType.KNIGHT: 3,
            PieceType.BISHOP: 3,
            PieceType.ROOK: 5,
            PieceType.QUEEN: 9,
            PieceType.KING: 0,  # King doesn't count for material
        }

        # Count current pieces on board
        white_counts: dict[PieceType, int] = dict.fromkeys(PieceType, 0)
        black_counts: dict[PieceType, int] = dict.fromkeys(PieceType, 0)

        for rank in self.board:
            for piece in rank:
                if piece:
                    if piece.color == Color.WHITE:
                        white_counts[piece.type] += 1
                    else:
                        black_counts[piece.type] += 1

        # Calculate captured pieces (white captures black pieces, black captures white pieces)
        white_captured: list[PieceType] = []
        black_captured: list[PieceType] = []

        for piece_type in PieceType:
            # White captured black pieces
            black_missing = starting_counts[piece_type] - black_counts[piece_type]
            white_captured.extend([piece_type] * black_missing)

            # Black captured white pieces
            white_missing = starting_counts[piece_type] - white_counts[piece_type]
            black_captured.extend([piece_type] * white_missing)

        self.captured_pieces = {
            Color.WHITE: white_captured,
            Color.BLACK: black_captured,
        }

        # Calculate material advantage (positive = white ahead, negative = black ahead)
        white_material = sum(piece_values[pt] * white_counts[pt] for pt in PieceType)
        black_material = sum(piece_values[pt] * black_counts[pt] for pt in PieceType)
        self.material_advantage = white_material - black_material

    @property
    def fen(self) -> str:
        """Get FEN (Forsyth-Edwards Notation) string representation of the current position."""
        chess_board = self.get_chess_board()
        return chess_board.fen()


class ChessStateView(BaseGameStateView):
    # Must remain here as it provides the concrete type of the events.
    events: list[ChessPlayerViewEvent] = Field(default_factory=list)
    board: ChessBoardMap = Field(..., description="Board as coordinate map (e.g., 'a1', 'e4') to pieces")
    side_to_move: Color = Field(..., description="Side to move next")
    castling_rights: CastlingRights = Field(..., description="Castling rights")
    en_passant_square: str | None = Field(default=None, description="Square available for en passant (e.g., 'e3')")
    halfmove_clock: int = Field(..., ge=0)
    fullmove_number: int = Field(..., ge=1)
    players: list[PlayerId] = Field(default_factory=list, description="List of player IDs in the game")
    remaining_time_ms: dict[PlayerId, int] = Field(default_factory=dict)
    last_timestamp_ms: int | None = Field(default=None)
    captured_pieces: dict[Color, list[PieceType]] = Field(
        default_factory=lambda: {Color.WHITE: [], Color.BLACK: []}, description="Pieces captured by each color"
    )
    material_advantage: int = Field(default=0, description="Material advantage for white")
    is_finished: bool = Field(default=False)
    winner: PlayerId | None = Field(default=None)
    draw_reason: DrawReason | None = Field(default=None)


# ----------------------------------
# Moves and possible moves
# ----------------------------------


class ChessMoveData(BasePlayerMoveData):
    """A chess move in coordinate notation."""

    from_square: str = Field(..., description="From square (e.g., 'e2')")
    to_square: str = Field(..., description="To square (e.g., 'e4')")
    promotion: Literal["q", "r", "b", "n"] | None = Field(default=None, description="Promotion piece (lowercase initial)")


class ChessPossibleMove(JsonModel):
    from_square: str = Field(..., description="Starting square in algebraic notation (e.g., 'e2')")
    to_square: str = Field(..., description="Destination square in algebraic notation (e.g., 'e4')")
    piece: PieceType = Field(..., description="Type of piece being moved (pawn, knight, bishop, rook, queen, king)")
    is_check: bool = Field(..., description="Whether this move puts the opponent's king in check")
    promotion: list[Literal["q", "r", "b", "n"]] | None = Field(default=None, description="Available promotion pieces if this is a pawn promotion move")


class ChessPossibleMoves(BasePlayerPossibleMoves):
    possible_moves: list[ChessPossibleMove] = Field(default_factory=list)


# ----------------------------------
# Events
# ----------------------------------


class ChessEventType(StrEnum):
    GAME_INITIALIZED = "game_initialized"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    MOVE_PLAYED = "move_played"
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    GAME_FINISHED = "game_finished"
    AGENT_REASONING = "agent_reasoning"
    CHAT_MESSAGE = "chat_message"
    MOVE_ANALYSIS = "move_analysis"
    AGENT_FORFEIT = "agent_forfeit"


class BaseChessEvent[T: ChessEventType](BaseGameEvent):
    type: T = Field(..., description="Event type")


class GameInitializedEvent(BaseChessEvent[ChessEventType.GAME_INITIALIZED]):
    type: Literal[ChessEventType.GAME_INITIALIZED] = ChessEventType.GAME_INITIALIZED
    game_id: GameId = Field(...)


class PlayerJoinedEvent(BaseChessEvent[ChessEventType.PLAYER_JOINED]):
    type: Literal[ChessEventType.PLAYER_JOINED] = ChessEventType.PLAYER_JOINED
    player_id: PlayerId = Field(..., description="Player ID")
    agent_version_id: AgentVersionId = Field(..., description="Agent version ID")
    name: str = Field(..., description="Player name")


class PlayerLeftEvent(BaseChessEvent[ChessEventType.PLAYER_LEFT]):
    """Event emitted when a player leaves the game."""

    type: Literal[ChessEventType.PLAYER_LEFT] = ChessEventType.PLAYER_LEFT
    player_id: PlayerId = Field(..., description="ID of player who left")
    reason: str = Field(default="disconnect", description="Reason for leaving")
    turn: int = Field(..., description="Round when player left")


class MovePlayedEvent(BaseChessEvent[ChessEventType.MOVE_PLAYED]):
    type: Literal[ChessEventType.MOVE_PLAYED] = ChessEventType.MOVE_PLAYED
    player_id: PlayerId = Field(...)
    from_square: str = Field(...)
    to_square: str = Field(...)
    promotion: Literal["q", "r", "b", "n"] | None = Field(default=None)
    is_capture: bool = Field(default=False)


class CheckEvent(BaseChessEvent[ChessEventType.CHECK]):
    type: Literal[ChessEventType.CHECK] = ChessEventType.CHECK
    side_in_check: Color = Field(..., description="Side that is currently in check")


class CheckmateEvent(BaseChessEvent[ChessEventType.CHECKMATE]):
    type: Literal[ChessEventType.CHECKMATE] = ChessEventType.CHECKMATE
    winner: PlayerId = Field(...)


class StalemateEvent(BaseChessEvent[ChessEventType.STALEMATE]):
    type: Literal[ChessEventType.STALEMATE] = ChessEventType.STALEMATE
    reason: str | None = Field(default=None)


class GameFinishedEvent(BaseChessEvent[ChessEventType.GAME_FINISHED]):
    type: Literal[ChessEventType.GAME_FINISHED] = ChessEventType.GAME_FINISHED
    winner: PlayerId | None = Field(default=None)
    draw_reason: DrawReason | None = Field(default=None)
    forfeit_reason: ForfeitReason | None = Field(default=None, description="Reason for forfeit (if applicable)")


class AgentReasoningEvent(ReasoningEventMixin, BaseChessEvent[ChessEventType.AGENT_REASONING]):
    type: Literal[ChessEventType.AGENT_REASONING] = ChessEventType.AGENT_REASONING


class ChatMessageEvent(ChatMessageMixin, BaseChessEvent[ChessEventType.CHAT_MESSAGE]):
    type: Literal[ChessEventType.CHAT_MESSAGE] = ChessEventType.CHAT_MESSAGE


class MoveAnalysisEvent(BaseChessEvent[ChessEventType.MOVE_ANALYSIS]):
    """Event emitted when a move has been analyzed by Stockfish and LLM."""

    type: Literal[ChessEventType.MOVE_ANALYSIS] = ChessEventType.MOVE_ANALYSIS
    round_number: int = Field(..., description="Round number when move was played")
    player_id: PlayerId = Field(..., description="Player who made the move")
    move_san: str = Field(..., description="Move in Standard Algebraic Notation")
    evaluation_cp: int | None = Field(default=None, description="Position evaluation in centipawns after move")
    evaluation_mate: int | None = Field(default=None, description="Mate in N moves (positive=white wins, negative=black wins)")
    best_move_san: str | None = Field(default=None, description="Best move according to Stockfish")
    narrative: str = Field(..., description="Human-readable analysis narrative")
    is_blunder: bool = Field(default=False, description="Move loses significant advantage (>300cp)")
    is_mistake: bool = Field(default=False, description="Move loses moderate advantage (100-300cp)")
    is_inaccuracy: bool = Field(default=False, description="Move loses small advantage (50-100cp)")
    is_brilliant: bool = Field(default=False, description="Exceptional move that improves position significantly")
    is_good: bool = Field(default=False, description="Good move that improves position")


class AgentForfeitEvent(BaseChessEvent[ChessEventType.AGENT_FORFEIT]):
    """Event emitted when an agent forfeits due to failing to move within attempt limit."""

    type: Literal[ChessEventType.AGENT_FORFEIT] = ChessEventType.AGENT_FORFEIT
    player_id: PlayerId = Field(..., description="ID of the agent who forfeited")
    reason: str = Field(default="Failed to move within attempt limit", description="Reason for forfeit")


ChessEvent = Annotated[
    GameInitializedEvent
    | PlayerJoinedEvent
    | PlayerLeftEvent
    | MovePlayedEvent
    | CheckEvent
    | CheckmateEvent
    | StalemateEvent
    | GameFinishedEvent
    | AgentReasoningEvent
    | ChatMessageEvent
    | MoveAnalysisEvent
    | AgentForfeitEvent,
    Field(discriminator="type"),
]


class PlayerJoinedPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Player Joined"] = "Player Joined"
    player_id: PlayerId = Field(..., description="Player ID")
    name: str = Field(..., description="Player name")


class PlayerLeftPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Player Left"] = "Player Left"
    player_id: PlayerId = Field(..., description="ID of player who left")
    reason: str = Field(default="disconnect", description="Reason for leaving")


class MovePlayedPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Move Played"] = "Move Played"
    player_id: PlayerId = Field(...)
    from_square: str = Field(...)
    to_square: str = Field(...)
    promotion: Literal["q", "r", "b", "n"] | None = Field(default=None)
    is_capture: bool | None = Field(default=None)


class CheckPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Check"] = "Check"
    side_in_check: Color = Field(..., description="Side that is currently in check")


class CheckmatePlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Checkmate"] = "Checkmate"
    winner: PlayerId = Field(...)


class StalematePlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Stalemate"] = "Stalemate"
    reason: str | None = Field(default=None)


class GameFinishedPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Game Finished"] = "Game Finished"
    winner: PlayerId | None = Field(default=None)
    draw_reason: DrawReason | None = Field(default=None)


class AgentReasoningPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Agent Reasoning"] = "Agent Reasoning"
    player_id: PlayerId = Field(..., description="Player ID who made the reasoning")
    reasoning: AgentReasoning = Field(..., description="Agent reasoning data")


class ChatMessagePlayerViewEvent(ChatMessageMixin, BasePlayerViewEvent):
    event: Literal["Chat Message"] = "Chat Message"


class MoveAnalysisPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Move Analysis"] = "Move Analysis"
    round_number: int = Field(...)
    player_id: PlayerId = Field(...)
    move_san: str = Field(...)
    evaluation_cp: int | None = Field(default=None)
    evaluation_mate: int | None = Field(default=None)
    best_move_san: str | None = Field(default=None)
    narrative: str = Field(...)
    is_blunder: bool = Field(default=False)
    is_mistake: bool = Field(default=False)
    is_inaccuracy: bool = Field(default=False)
    is_brilliant: bool = Field(default=False)
    is_good: bool = Field(default=False)


class AgentForfeitPlayerViewEvent(BasePlayerViewEvent):
    event: Literal["Agent Forfeit"] = "Agent Forfeit"
    player_id: PlayerId = Field(..., description="ID of the agent who forfeited")
    reason: str = Field(default="Failed to move within attempt limit", description="Reason for forfeit")


ChessPlayerViewEvent = Annotated[
    PlayerJoinedPlayerViewEvent
    | PlayerLeftPlayerViewEvent
    | MovePlayedPlayerViewEvent
    | CheckPlayerViewEvent
    | CheckmatePlayerViewEvent
    | StalematePlayerViewEvent
    | GameFinishedPlayerViewEvent
    | AgentReasoningPlayerViewEvent
    | ChatMessagePlayerViewEvent
    | MoveAnalysisPlayerViewEvent
    | AgentForfeitPlayerViewEvent,
    Field(discriminator="event"),
]


# ----------------------------------
# Agent decision
# ----------------------------------


class ChessAgentDecision(BaseAgentDecision[ChessMoveData]):
    pass


# ----------------------------------
# Board Representation
# ----------------------------------

type ChessBoardMap = dict[str, ChessPiece]  # Map from "a1", "a2", etc. to ChessPiece


def board_to_map(board: list[list[ChessPiece | None]]) -> ChessBoardMap:
    """Convert a 2D array board representation to a coordinate map representation.

    Args:
        board: 8x8 2D array where board[0][0] is a8 and board[7][7] is h1

    Returns:
        ChessBoardMap with coordinates as keys and pieces as values, sorted by rank
    """
    pieces: dict[str, ChessPiece] = {}

    # First collect all pieces with their coordinates
    for rank in range(8):
        for file in range(8):
            piece = board[rank][file]
            if piece is not None:
                # Convert array indices to chess coordinates
                # rank 0 -> 8, rank 7 -> 1
                # file 0 -> a, file 7 -> h
                coord = f"{chr(97 + file)}{8 - rank}"
                pieces[coord] = piece

    # Sort by rank (1-8) then by file (a-h) for consistent ordering
    sorted_pieces: dict[str, ChessPiece] = {}
    for rank_num in range(1, 9):  # 1 to 8
        for file_char in FILES:
            coord = f"{file_char}{rank_num}"
            if coord in pieces:
                sorted_pieces[coord] = pieces[coord]

    return sorted_pieces


def map_to_board(board_map: ChessBoardMap) -> list[list[ChessPiece | None]]:
    """Convert a coordinate map representation to a 2D array board representation.

    Args:
        board_map: ChessBoardMap with coordinates as keys and pieces as values

    Returns:
        8x8 2D array where board[0][0] is a8 and board[7][7] is h1
    """
    board: list[list[ChessPiece | None]] = [[None for _ in range(8)] for _ in range(8)]

    for coord, piece in board_map.items():
        if len(coord) != 2:
            continue

        file_char = coord[0]
        rank_char = coord[1]

        if file_char < "a" or file_char > "h" or rank_char < "1" or rank_char > "8":
            continue

        file = ord(file_char) - ord("a")  # a=0, b=1, ..., h=7
        rank = 8 - int(rank_char)  # 8->0, 7->1, ..., 1->7

        board[rank][file] = piece

    return board


# ----------------------------------
# Helpers
# ----------------------------------

FILES = ("a", "b", "c", "d", "e", "f", "g", "h")


def create_starting_board() -> list[list[ChessPiece | None]]:
    """Create the standard chess starting position (8x8 array)."""

    def piece(pt: PieceType, c: Color) -> ChessPiece:
        return ChessPiece(type=pt, color=c)

    # Empty rank
    empty: list[ChessPiece | None] = [None] * 8

    # White pieces (bottom, rank 1 and 2)
    rank1: list[ChessPiece | None] = [
        piece(PieceType.ROOK, Color.WHITE),
        piece(PieceType.KNIGHT, Color.WHITE),
        piece(PieceType.BISHOP, Color.WHITE),
        piece(PieceType.QUEEN, Color.WHITE),
        piece(PieceType.KING, Color.WHITE),
        piece(PieceType.BISHOP, Color.WHITE),
        piece(PieceType.KNIGHT, Color.WHITE),
        piece(PieceType.ROOK, Color.WHITE),
    ]
    rank2: list[ChessPiece | None] = [piece(PieceType.PAWN, Color.WHITE) for _ in range(8)]

    # Black pieces (top, rank 8 and 7)
    rank8: list[ChessPiece | None] = [
        piece(PieceType.ROOK, Color.BLACK),
        piece(PieceType.KNIGHT, Color.BLACK),
        piece(PieceType.BISHOP, Color.BLACK),
        piece(PieceType.QUEEN, Color.BLACK),
        piece(PieceType.KING, Color.BLACK),
        piece(PieceType.BISHOP, Color.BLACK),
        piece(PieceType.KNIGHT, Color.BLACK),
        piece(PieceType.ROOK, Color.BLACK),
    ]
    rank7: list[ChessPiece | None] = [piece(PieceType.PAWN, Color.BLACK) for _ in range(8)]

    # Board is rank8..rank1 top->bottom (UI can map as needed)
    return [
        rank8,
        rank7,
        empty.copy(),
        empty.copy(),
        empty.copy(),
        empty.copy(),
        rank2,
        rank1,
    ]
