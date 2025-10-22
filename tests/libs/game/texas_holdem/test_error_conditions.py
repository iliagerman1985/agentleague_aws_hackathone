"""Comprehensive tests for all error conditions in Texas Hold'em."""

import pytest
from texas_holdem import BettingRound, TexasHoldemAction, TexasHoldemMoveData
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from common.ids import AgentId

from .test_helpers import PLAYER_1, PLAYER_2, PokerTest


class TestErrorConditions:
    """Comprehensive test for all error conditions and invalid move validation."""

    def test_all_error_conditions(self) -> None:
        """Test all error conditions in one comprehensive test."""

        # === Pydantic Validation Errors ===

        # Invalid player ID
        with pytest.raises(ValueError):
            _ = TexasHoldemMoveData(
                player_id="invalid_player",  # type: ignore
                action=TexasHoldemAction.CALL,
                amount=None,
            )

        # Invalid action type
        with pytest.raises(ValueError):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action="invalid_action",  # type: ignore
                amount=None,
            )

        # Negative raise amount
        with pytest.raises(ValueError):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action=TexasHoldemAction.RAISE,
                amount=-10,
            )

        # Fold/check with amount
        with pytest.raises(Exception):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action=TexasHoldemAction.FOLD,
                amount=100,
            )

        # === Game Logic Errors ===

        test = PokerTest.create()

        # NOT_PLAYER_TURN: Try to make player_2 act when it's player_1's turn
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.CALL, expected_error=THErrors.NOT_PLAYER_TURN)

        # PLAYER_NOT_ACTIVE: Folded player cannot act
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CALL, expected_error=THErrors.NOT_PLAYER_TURN)

        # PLAYER_NOT_ACTIVE: All-in player cannot act further
        test = PokerTest.create(chips={PLAYER_1: 5})
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)  # Goes all-in with insufficient chips
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CHECK, expected_error=THErrors.NOT_PLAYER_TURN)

        # NO_CHIPS: Player with zero chips cannot act
        test = PokerTest.create(chips={PLAYER_1: 0})
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.ALL_IN, expected_error=THErrors.NO_CHIPS)

        # CANNOT_CHECK: Cannot check when there's a bet to call
        test = PokerTest.create()
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.CHECK, expected_error=THErrors.CANNOT_CHECK)

        # NO_BET_TO_CALL: Cannot call when there's no bet
        test = PokerTest.create(betting_round=BettingRound.FLOP, current_bet=0)
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.CALL, expected_error=THErrors.NO_BET_TO_CALL)

        # MISSING_AMOUNT: Raise without amount
        test = PokerTest.create()
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.RAISE, expected_error=THErrors.MISSING_AMOUNT)

        # RAISE_TOO_SMALL: Raise amount too small
        test = PokerTest.create()
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.RAISE, amount=15, expected_error=THErrors.RAISE_TOO_SMALL)
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.RAISE, amount=0, expected_error=THErrors.RAISE_TOO_SMALL)

        # VALIDATION_ERROR: Negative raise amount (caught by game logic)
        test = PokerTest.create()
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.RAISE, amount=-10, expected_error=THErrors.VALIDATION_ERROR)

        # GAME_OVER: Move after game is finished
        test = PokerTest.create(num_players=2)
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)  # Game ends
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.CHECK, expected_error=THErrors.GAME_OVER)

        # INVALID_ACTION: Move during showdown
        test = PokerTest.create(betting_round=BettingRound.SHOWDOWN)
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CALL, expected_error=THErrors.INVALID_ACTION)

        # Double big blind rule violation
        test = PokerTest.create()
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=20)  # Minimum raise
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.RAISE, amount=25, expected_error=THErrors.RAISE_TOO_SMALL)  # Only 5 more

        # Test with non-existent player ID in game context
        test = PokerTest.create()
        _ = test.process_move_error(AgentId("invalid_player"), TexasHoldemAction.CALL, expected_error=THErrors.NOT_PLAYER_TURN)
