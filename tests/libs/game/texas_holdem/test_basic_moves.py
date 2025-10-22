"""Tests for basic poker moves: fold, call, check, raise, all-in."""

import pytest
from game_api import GameType
from texas_holdem import BettingRound, PlayerStatus, TexasHoldemAction, TexasHoldemMoveData, TexasHoldemPlayer, TexasHoldemState
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from common.core.app_error import AppException

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff

# TODO: All in can be below min raise, check it in preflop and postflop.
# TODO: Test for rounds where everyone checks, both normal game and heads-up
# TODO: Test that rounds don't close until everyone settles the bet.
# TODO: Test hand transitions after someone won.


class TestBasicPokerMoves:
    """Test basic poker moves through the GameManager interface."""

    def test_fold_action(self) -> None:
        """Test fold action removes player from hand."""
        test = PokerTest.create()

        # Player 1 folds (UTG position)
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.FOLD,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

    def test_call_action(self) -> None:
        """Test call action matches current bet."""
        test = PokerTest.create()

        # Player 1 calls the big blind (10)
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=25,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

    def test_call_insufficient_chips(self) -> None:
        """Test call with insufficient chips goes all-in."""
        test = PokerTest.create(chips={PLAYER_1: 8})

        # Player 1 has 8 chips, tries to call 10 but goes all-in with remaining chips
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN, current_bet=8, total_bet=8)},
                pot=23,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

    def test_check_action(self) -> None:
        """Test check action in a normal 3-player check flow."""
        test = PokerTest.create(num_players=3)

        # Complete preflop betting round:
        # Player 1 (UTG) calls
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_2, action_position=1, players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=25
            ),
        )

        # Player 2 (SB) calls
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_3, action_position=2, players={PLAYER_2: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=30
            ),
        )

        # Player 3 (BB) checks - this completes preflop and advances to flop
        test.process_move(
            PLAYER_3,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                current_player_id=PLAYER_2,
                action_position=1,
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(current_bet=0),
                    PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                    PLAYER_3: TexasHoldemPlayerDiff(current_bet=0),
                },
            ),
        )

        # Flop round - all players check:
        # Player 2 (SB) checks first
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(current_player_id=PLAYER_3, action_position=2),
        )

        # Player 3 checks
        test.process_move(
            PLAYER_3,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(current_player_id=PLAYER_1, action_position=0),
        )

        # Player 1 checks - this should advance to TURN round
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(betting_round=BettingRound.TURN, current_player_id=PLAYER_2, action_position=1),
        )

    def test_check_heads_up(self) -> None:
        """Test check action in heads up."""
        # Create a heads-up game where checking is simpler
        test = PokerTest.create(num_players=2)

        # Player 1 (dealer/small blind) calls to match big blind
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_2, action_position=1, players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=20
            ),
        )

        # Player 2 (big blind) checks
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                players={PLAYER_1: TexasHoldemPlayerDiff(current_bet=0), PLAYER_2: TexasHoldemPlayerDiff(current_bet=0)},
            ),
        )

        # Now we're in the flop, big blind acts first and can check
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(current_player_id=PLAYER_1, action_position=0),
        )

    def test_check_with_bet_to_call_fails(self) -> None:
        """Test check fails when there's a bet to call."""
        test = PokerTest.create()

        # Player 1 tries to check when big blind is 10
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CHECK, expected_error=THErrors.CANNOT_CHECK)

    def test_raise_action(self) -> None:
        """Test raise action increases bet."""
        test = PokerTest.create()

        # Player 1 raises to 30 (20 more than current bet of 10)
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=30,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=45,
                current_bet=30,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=20,
                last_raise_position=0,
            ),
        )

    def test_raise_too_small_fails(self) -> None:
        """Test raise that's too small fails."""
        test = PokerTest.create()

        # Player 1 tries to raise by only 5 (less than big blind of 10)
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.RAISE, amount=15, expected_error=THErrors.RAISE_TOO_SMALL)

    def test_all_in_smaller_than_minimal_raise_succeeds(self) -> None:
        """Test all-in that's smaller than minimal raise succeeds."""
        test = PokerTest.create(chips={PLAYER_1: 15, PLAYER_2: 1000})

        # Player 1 goes all-in
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.ALL_IN,
            expected_state_diff=TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(
                        chips=0,
                        status=PlayerStatus.ALL_IN,
                        current_bet=15,
                        total_bet=15,
                    )
                },
                pot=30,
                current_bet=15,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_position=0,
            ),
        )

    def test_raise_insufficient_chips(self) -> None:
        """Test raise with insufficient chips goes all-in."""
        test = PokerTest.create(chips={PLAYER_1: 25})

        # Player 1 tries to raise to 50 but only has 25
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=50,
            expected_state_diff=TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(
                        chips=0,
                        status=PlayerStatus.ALL_IN,
                        current_bet=25,
                        total_bet=25,
                    )
                },
                pot=40,
                current_bet=25,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=15,
                last_raise_position=0,
            ),
        )

    def test_all_in_action(self) -> None:
        """Test all-in action puts all chips in pot."""
        test = PokerTest.create()

        # Player 1 goes all-in
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.ALL_IN,
            expected_state_diff=TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(
                        chips=0,
                        status=PlayerStatus.ALL_IN,
                        current_bet=1000,
                        total_bet=1000,
                    )
                },
                pot=1015,
                current_bet=1000,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=990,
                last_raise_position=0,
            ),
        )

    def test_all_in_no_chips_fails(self) -> None:
        """Test all-in fails when player has no chips."""
        test = PokerTest.create(chips={PLAYER_1: 0})

        # Player 1 tries to go all-in with no chips
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.ALL_IN, expected_error=THErrors.NO_CHIPS)

    def test_move_out_of_turn_fails(self) -> None:
        """Test move fails when it's not player's turn."""
        test = PokerTest.create()

        # Player 2 tries to act when it's player 1's turn
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.FOLD, expected_error=THErrors.NOT_PLAYER_TURN)

    def test_folded_player_cannot_act(self) -> None:
        """Test folded player cannot make moves."""
        test = PokerTest.create(num_players=3)

        # Fold player 1 first (dealer)
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.FOLD,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

        # Complete the round so we can test in next round
        test.process_move(  # SB calls
            PLAYER_2,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(current_bet=10, total_bet=10, chips=990)},
                pot=20,
                current_player_id=PLAYER_3,
                action_position=2,
            ),
        )
        test.process_move(  # BB checks
            PLAYER_3,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                players={PLAYER_2: TexasHoldemPlayerDiff(current_bet=0), PLAYER_3: TexasHoldemPlayerDiff(current_bet=0)},
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

        # Now in flop, try to have folded player act
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CHECK, expected_error=THErrors.NOT_PLAYER_TURN)

    def test_raise_without_amount_fails(self) -> None:
        """Test raise without specifying amount fails."""
        # Try to create a raise move without amount (should fail at Pydantic level)
        with pytest.raises(AppException, match="Raise action requires an amount"):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action=TexasHoldemAction.RAISE,
                amount=None,
            )

    def test_negative_raise_fails(self) -> None:
        """Test negative raise fails."""
        # Try to create a raise move with negative amount (should fail at Pydantic level)
        with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action=TexasHoldemAction.RAISE,
                amount=-10,
            )

    def test_fold_check_with_amount_fails(self) -> None:
        """Test fold/check with amount fails."""
        # Try to create fold with amount (should fail at Pydantic level)
        with pytest.raises(AppException, match="Action fold should not have an amount"):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action=TexasHoldemAction.FOLD,
                amount=100,
            )

        # Try to create check with amount (should fail at Pydantic level)
        with pytest.raises(AppException, match="Action check should not have an amount"):
            _ = TexasHoldemMoveData(
                player_id=PLAYER_1,
                action=TexasHoldemAction.CHECK,
                amount=100,
            )

    def test_sequential_moves(self) -> None:
        """Test sequence of moves in a betting round."""
        test = PokerTest.create(num_players=3)

        test.assert_state(
            TexasHoldemState(
                game_id=test.state.game_id,
                env=GameType.TEXAS_HOLDEM,
                is_finished=False,
                current_player_id=PLAYER_1,
                turn=1,
                players=[
                    TexasHoldemPlayer(
                        player_id=PLAYER_1,
                        chips=1000,
                        status=PlayerStatus.ACTIVE,
                        current_bet=0,
                        total_bet=0,
                        position=0,
                    ),
                    TexasHoldemPlayer(
                        player_id=PLAYER_2,
                        chips=995,
                        status=PlayerStatus.ACTIVE,
                        current_bet=5,
                        total_bet=5,
                        position=1,
                    ),
                    TexasHoldemPlayer(
                        player_id=PLAYER_3,
                        chips=990,
                        status=PlayerStatus.ACTIVE,
                        current_bet=10,
                        total_bet=10,
                        position=2,
                    ),
                ],
                pot=15,
                current_bet=10,
                betting_round=BettingRound.PREFLOP,
                dealer_position=0,
                small_blind_position=1,
                big_blind_position=2,
                action_position=0,
                last_raise_amount=0,
            ),
        )

        # Player 1 calls the big blind
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=25,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

        # Player 2 (small blind) raises
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=30,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=50,
                current_bet=30,
                current_player_id=PLAYER_3,
                action_position=2,
                last_raise_amount=20,
                last_raise_position=1,
            ),
        )

        # Player 3 (big blind) calls the raise
        test.process_move(
            PLAYER_3,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=70,
                current_player_id=PLAYER_1,
                action_position=0,
            ),
        )

        # Player 1 needs to call to match the raise
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(chips=970, current_bet=0, total_bet=30),
                    PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                    PLAYER_3: TexasHoldemPlayerDiff(current_bet=0),
                },
                pot=90,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=0,
            ),
        )

        # After this call, the betting round should complete and advance to flop
        test.assert_state(
            TexasHoldemState(
                game_id=test.state.game_id,
                env=GameType.TEXAS_HOLDEM,
                is_finished=False,
                turn=1,
                players=[
                    TexasHoldemPlayer(
                        player_id=PLAYER_1,
                        chips=970,
                        status=PlayerStatus.ACTIVE,
                        current_bet=0,
                        total_bet=30,
                        position=0,
                    ),
                    TexasHoldemPlayer(
                        player_id=PLAYER_2,
                        chips=970,
                        status=PlayerStatus.ACTIVE,
                        current_bet=0,
                        total_bet=30,
                        position=1,
                    ),
                    TexasHoldemPlayer(
                        player_id=PLAYER_3,
                        chips=970,
                        status=PlayerStatus.ACTIVE,
                        current_bet=0,
                        total_bet=30,
                        position=2,
                    ),
                ],
                pot=90,
                current_bet=0,
                betting_round=BettingRound.FLOP,
                dealer_position=0,
                small_blind_position=1,
                big_blind_position=2,
                action_position=1,
                current_player_id=PLAYER_2,
            ),
        )

    def test_minimum_raise_validation(self) -> None:
        """Test minimum raise amounts in different scenarios."""
        test = PokerTest.create(num_players=3)

        # Round bet is 10, player 1 has current bet 0. Invalid raise (19 = current_bet(10) + 9), 9 is less than BB in preflop (10).
        _ = test.process_move_error(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=19,
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid raise, equals BB.
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=20,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=980, current_bet=20, total_bet=20)},
                pot=35,
                current_bet=20,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=10,
                last_raise_position=0,
            ),
        )

        # Round bet is 20, player 2 has current bet 5 (SB). Invalid raise amount (29 = current_bet(20) + 9), less than last raise (10).
        _ = test.process_move_error(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=29,
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid raise, equals last raise
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=30,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=60,
                current_bet=30,
                current_player_id=PLAYER_3,
                action_position=2,
                last_raise_position=1,
            ),
        )

        # Round bet is 30, player 3 has current bet 10 (BB). Invalid raise amount (39 = current_bet(30) + 9), less than last raise (10).
        _ = test.process_move_error(
            PLAYER_3,
            TexasHoldemAction.RAISE,
            amount=39,
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid raise (40 = current_bet(30) + 10), equals last raise (10).
        test.process_move(
            PLAYER_3,
            TexasHoldemAction.RAISE,
            amount=40,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=960, current_bet=40, total_bet=40)},
                pot=90,
                current_bet=40,
                current_player_id=PLAYER_1,
                action_position=0,
                last_raise_position=2,
            ),
        )

        # Round bet is 40, player 1 has current bet 20. Valid raise (60 = current_bet(40) + 20), greater than last raise (10).
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=60,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=940, current_bet=60, total_bet=60)},
                pot=130,
                current_bet=60,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_position=0,
                last_raise_amount=20,
            ),
        )

        # Round bet is 60, player 2 has current bet 30. Invalid raise amount (79 = current_bet(60) + 19), less than last raise (20).
        _ = test.process_move_error(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=79,
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid raise (90 = current_bet(60) + 30), greater than last raise (20).
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=90,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=910, current_bet=90, total_bet=90)},
                pot=190,
                current_bet=90,
                current_player_id=PLAYER_3,
                action_position=2,
                last_raise_position=1,
                last_raise_amount=30,
            ),
        )

        # Finish this betting round and move on to the next. Player 3 & 1 call.
        test.process_move(
            PLAYER_3,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=910, current_bet=90, total_bet=90)},
                pot=240,
                current_player_id=PLAYER_1,
                action_position=0,
            ),
        )
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(chips=910, current_bet=0, total_bet=90),
                    PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                    PLAYER_3: TexasHoldemPlayerDiff(current_bet=0),
                },
                pot=270,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=0,
            ),
        )

        # Minimum bet in flop is BB.
        # FIXME: Need a special action called Bet which can only be used if there's no previous bet.
        _ = test.process_move_error(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=9,
            expected_error=THErrors.RAISE_TOO_SMALL,
        )
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=10,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=900, current_bet=10, total_bet=100)},
                pot=280,
                current_bet=10,
                current_player_id=PLAYER_3,
                action_position=2,
                last_raise_position=1,
                last_raise_amount=10,
            ),
        )

        _ = test.process_move_error(
            PLAYER_3,
            TexasHoldemAction.RAISE,
            amount=19,
            expected_error=THErrors.RAISE_TOO_SMALL,
        )
        test.process_move(
            PLAYER_3,
            TexasHoldemAction.RAISE,
            amount=20,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=890, current_bet=20, total_bet=110)},
                pot=300,
                current_bet=20,
                current_player_id=PLAYER_1,
                action_position=0,
                last_raise_position=2,
            ),
        )

    def test_minimum_raise_with_all_in_player(self) -> None:
        """Test minimum raise calculation when a player goes all-in."""
        test = PokerTest.create(chips={PLAYER_2: 15})

        # Player 1 raises to 30
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)

        # Player 2 goes all-in with 15 chips (incomplete raise)
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=15)

        # Player 3 can still raise by the original minimum (20 from the first raise)
        # So minimum total bet is 30 + 20 = 50
        test.process_move(PLAYER_3, TexasHoldemAction.RAISE, amount=50)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_4, current_bet=50))

    def test_minimum_raise_with_incomplete_all_in(self) -> None:
        """Test minimum raise when previous all-in was incomplete."""
        test = PokerTest.create(chips={PLAYER_1: 25, PLAYER_2: 35})

        # Player 1 goes all-in with 25 chips (incomplete raise from big blind of 10)
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=25)

        # Player 2 can complete the raise to at least 20 (double big blind)
        # But since Player 1 only raised by 15, the minimum is still 20
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=35)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_3, current_bet=35))

    """Test edge cases for basic poker moves."""

    def test_exact_chip_boundary_raise(self) -> None:
        """Test raise with exact remaining chips considered all in."""
        test = PokerTest.create(chips={PLAYER_1: 50})

        # Player 1 raises exactly by all their remaining chips, should be ALL_IN
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=50,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_2,
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=50, total_bet=50, status=PlayerStatus.ALL_IN)},
                pot=65,
                current_bet=50,
                action_position=1,
                last_raise_amount=40,
                last_raise_position=0,
            ),
        )

    def test_move_with_exact_call_amount(self) -> None:
        """Test calling with exact amount needed."""
        test = PokerTest.create(num_players=3, chips={PLAYER_1: 1000, PLAYER_2: 45, PLAYER_3: 1000})

        # Player 1 raises
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=50,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_2,
                current_bet=50,
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=950, current_bet=50, total_bet=50)},
                pot=65,
                action_position=1,
                last_raise_amount=40,
                last_raise_position=0,
            ),
        )

        # Player 2 (SB) has exactly 45 chips remaining
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_3,
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=0, current_bet=45, total_bet=45, status=PlayerStatus.ALL_IN)},
                pot=105,
                action_position=2,
            ),
        )

    def test_action_after_game_state_change(self) -> None:
        """Test move validation after game state changes."""
        test = PokerTest.create()

        # Player 1 folds
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.FOLD,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_2,
                players={PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                action_position=1,
            ),
        )

        # Verify folded player cannot act
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CALL, expected_error=THErrors.NOT_PLAYER_TURN)

    def test_all_in_with_partial_blind(self) -> None:
        """Test all-in behavior when player can't afford full blind."""
        # Create a new test with custom chip configuration
        test = PokerTest.create(num_players=3, chips={PLAYER_1: 1000, PLAYER_2: 3, PLAYER_3: 1000})

        # The blind structure is automatically set up by PokerTest.create()
        # Player 2 (small blind) should have insufficient chips for full small blind
        # Verify the initial state after blind posting
        test.assert_state(
            TexasHoldemState(
                game_id=test.state.game_id,
                env=test.state.env,
                players=[
                    TexasHoldemPlayer(player_id=PLAYER_1, chips=1000, current_bet=0, total_bet=0, status=PlayerStatus.ACTIVE, position=0),
                    TexasHoldemPlayer(player_id=PLAYER_2, chips=0, current_bet=3, total_bet=3, status=PlayerStatus.ALL_IN, position=1),
                    TexasHoldemPlayer(player_id=PLAYER_3, chips=990, current_bet=10, total_bet=10, status=PlayerStatus.ACTIVE, position=2),
                ],
                current_player_id=PLAYER_1,
                action_position=0,
                betting_round=BettingRound.PREFLOP,
                current_bet=10,
                pot=13,
                small_blind_position=1,
                big_blind_position=2,
            )
        )

    def test_raise_followed_by_check(self) -> None:
        """Test raise followed by check in same round."""
        test = PokerTest.create()

        # Player 1 raises in preflop
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=50)

        # Now player 2 cannot check because there's a bet to call
        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.CHECK, expected_error=THErrors.CANNOT_CHECK)
