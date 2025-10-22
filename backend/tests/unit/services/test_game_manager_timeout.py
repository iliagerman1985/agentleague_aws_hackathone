"""Unit tests for GameManager.finalize_timeout."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from chess_game.chess_api import CastlingRights, ChessConfig, ChessState, Color, DrawReason, create_starting_board
from game_api import BaseGameEvent, EventCollector, GameType

from app.services.game_manager import GameManager
from common.core.app_error import AppException, Errors
from common.ids import AgentVersionId, GameId, PlayerId, RequestId, UserId
from common.utils.tsid import TSID
from shared_db.models.game import Game, GamePlayer, MatchmakingStatus


class FakeChessEnvTypes:
    """Minimal Chess environment type for testing."""

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
    def event_type(cls):  # pragma: no cover - not used in tests
        return object

    @classmethod
    def player_move_type(cls):  # pragma: no cover - not used in tests
        return object

    @classmethod
    def player_view_type(cls):  # pragma: no cover - not used in tests
        return object

    @classmethod
    def possible_moves_type(cls):  # pragma: no cover - not used in tests
        return object

    @classmethod
    def agent_decision_type(cls):  # pragma: no cover - not used in tests
        return object

    @classmethod
    def reasoning_event_type(cls):  # pragma: no cover - not used in tests
        return object

    @classmethod
    def create_reasoning_event(cls, turn, player_id, reasoning):  # pragma: no cover - not used
        raise NotImplementedError

    @classmethod
    def create_chat_event(cls, turn, player_id, message):  # pragma: no cover - not used
        raise NotImplementedError

    @classmethod
    def default_config(cls) -> ChessConfig:  # pragma: no cover - not used
        return ChessConfig()

    @classmethod
    def config_ui_options(cls) -> dict[str, object]:  # pragma: no cover - not used
        return {}


class FakeChessEnv:
    """Minimal Chess environment that only implements timeout checking."""

    def __init__(self, config: ChessConfig) -> None:
        self.config = config

    @classmethod
    def types(cls) -> type[FakeChessEnvTypes]:
        return FakeChessEnvTypes

    @classmethod
    def create(cls, config: ChessConfig) -> "FakeChessEnv":
        return cls(config)

    def check_timeout(self, state: ChessState, event_collector: EventCollector[BaseGameEvent]) -> bool:
        remaining = state.remaining_time_ms.get(state.current_player_id, 0)
        if remaining > 0:
            return False

        # Mark the game as finished and pick the opponent as the winner
        state.is_finished = True
        opponent = next((pid for pid in state.players if pid != state.current_player_id), None)
        state.winner = opponent
        state.draw_reason = DrawReason.TIME
        return True


def _build_game(remaining_ms_current: int) -> tuple[Game, PlayerId, PlayerId, UserId]:
    request_user = UserId(TSID.create())
    game_id = GameId(TSID.create())
    white_player = PlayerId(TSID.create())
    black_player = PlayerId(TSID.create())

    state = ChessState.model_validate(
        {
            "game_id": game_id,
            "env": GameType.CHESS,
            "turn": 4,
            "current_player_id": white_player,
            "board": create_starting_board(),
            "side_to_move": Color.WHITE,
            "castling_rights": CastlingRights(),
            "en_passant_square": None,
            "halfmove_clock": 0,
            "fullmove_number": 3,
            "players": [white_player, black_player],
            "remaining_time_ms": {white_player: remaining_ms_current, black_player: 120000},
            "last_timestamp_ms": 0,
        }
    )

    config = ChessConfig()

    game = Game(
        id=game_id,
        game_type=GameType.CHESS,
        state=state.model_dump(mode="python"),
        config=config.model_dump(mode="python"),
        requesting_user_id=request_user,
        matchmaking_status=MatchmakingStatus.IN_PROGRESS,
        is_playground=False,
    )

    join_time = datetime.now(UTC)
    player1 = GamePlayer(
        id=white_player,
        game_id=game_id,
        agent_version_id=AgentVersionId(TSID.create()),
        user_id=request_user,
        env=GameType.CHESS,
        join_time=join_time,
        is_system_player=False,
    )
    player2 = GamePlayer(
        id=black_player,
        game_id=game_id,
        agent_version_id=AgentVersionId(TSID.create()),
        user_id=UserId(TSID.create()),
        env=GameType.CHESS,
        join_time=join_time,
        is_system_player=False,
    )
    game.game_players = [player1, player2]

    return game, white_player, black_player, request_user


def _build_manager(game: Game, registry: MagicMock) -> tuple[GameManager, MagicMock, AsyncMock]:
    agent_execution_service = MagicMock()
    game_dao = MagicMock()
    game_dao.start_processing = AsyncMock(return_value=game)
    game_dao.finish_processing = AsyncMock(return_value=None)
    game_dao.set_state = AsyncMock(return_value=None)
    game_dao.add_events = AsyncMock(return_value=None)
    game_dao.set_leave_time_for_game = AsyncMock(return_value=None)
    game_dao.set_status = AsyncMock(return_value=None)

    agent_version_dao = MagicMock()
    tool_dao = MagicMock()
    llm_integration_service = MagicMock()
    agent_runner = MagicMock()
    scoring_service = MagicMock()

    manager = GameManager(
        registry=registry,
        agent_execution_service=agent_execution_service,
        game_dao=game_dao,
        agent_version_dao=agent_version_dao,
        tool_dao=tool_dao,
        llm_integration_service=llm_integration_service,
        agent_runner=agent_runner,
        scoring_service=scoring_service,
    )
    rating_mock = AsyncMock(return_value=None)
    manager._update_ratings_for_finished_game = rating_mock  # type: ignore[method-assign]
    return manager, game_dao, rating_mock


@pytest.mark.asyncio
async def test_finalize_timeout_marks_game_finished() -> None:
    registry = MagicMock()
    registry.get.return_value = FakeChessEnv

    game, current_pid, other_pid, requesting_user = _build_game(remaining_ms_current=0)
    manager, game_dao, rating_mock = _build_manager(game, registry)

    db = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.rollback = AsyncMock(return_value=None)

    result_state, events = await manager.finalize_timeout(
        db=db,
        request_id=RequestId(TSID.create()),
        game_id=game.id,
        requesting_user_id=requesting_user,
        expected_player_id=current_pid,
    )

    assert isinstance(result_state, ChessState)
    assert result_state.is_finished is True
    assert result_state.winner == other_pid
    assert result_state.draw_reason == DrawReason.TIME
    assert events == []

    assert game_dao.set_state.await_count == 1
    game_dao.set_leave_time_for_game.assert_awaited_once_with(db, game.id)
    game_dao.set_status.assert_awaited_once_with(db, game.id, MatchmakingStatus.FINISHED)
    game_dao.add_events.assert_not_awaited()
    game_dao.finish_processing.assert_awaited_once()
    db.commit.assert_awaited_once()
    rating_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_timeout_rejects_when_time_remaining() -> None:
    registry = MagicMock()
    registry.get.return_value = FakeChessEnv

    game, current_pid, _other_pid, requesting_user = _build_game(remaining_ms_current=5000)
    manager, game_dao, rating_mock = _build_manager(game, registry)

    db = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.rollback = AsyncMock(return_value=None)

    with pytest.raises(AppException) as exc_info:
        await manager.finalize_timeout(
            db=db,
            request_id=RequestId(TSID.create()),
            game_id=game.id,
            requesting_user_id=requesting_user,
            expected_player_id=current_pid,
        )

    assert exc_info.value.details.code == Errors.Generic.INVALID_INPUT.code
    assert exc_info.value.details.scope == Errors.Generic.INVALID_INPUT.scope

    game_dao.set_state.assert_not_called()
    game_dao.add_events.assert_not_called()
    game_dao.set_leave_time_for_game.assert_not_called()
    game_dao.set_status.assert_not_called()
    game_dao.finish_processing.assert_awaited_once()
    db.commit.assert_awaited_once()
    rating_mock.assert_not_called()
