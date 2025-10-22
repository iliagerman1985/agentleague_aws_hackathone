"""Tests for complex betting scenarios in Texas Hold'em."""

from texas_holdem import BettingRound, TexasHoldemAction
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest, TexasHoldemStateDiff


class TestComplexBetting:
    """Test complex betting scenarios and edge cases."""

    def test_multiple_raises_in_sequence(self) -> None:
        """Test multiple raises in sequence within a betting round."""

        test = PokerTest.create(num_players=4)

        # Player 1 raises to 30

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=30, current_player_id=PLAYER_2))

        # Player 2 re-raises to 60

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=60)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=60, current_player_id=PLAYER_3))

        # Player 3 re-raises to 120

        test.process_move(PLAYER_3, TexasHoldemAction.RAISE, amount=120)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=120, current_player_id=PLAYER_4))

    def test_minimum_raise_after_previous_raise(self) -> None:
        """Test minimum raise calculation after a previous raise."""

        test = PokerTest.create(num_players=3)

        # Player 1 raises to 30

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=30, current_player_id=PLAYER_2))

        # Player 2 tries to raise by less than minimum (should fail)

        _ = test.process_move_error(PLAYER_2, TexasHoldemAction.RAISE, amount=50, expected_error=THErrors.RAISE_TOO_SMALL)

        # Player 2 raises by exactly the minimum amount (should succeed)

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=60)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=60, current_player_id=PLAYER_3))

    def test_betting_round_completion_with_raises(self) -> None:
        """Test betting round completion after raises."""

        test = PokerTest.create(num_players=3)

        # Player 1 raises to 30

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=30, current_player_id=PLAYER_2))

        # Player 2 calls

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_3))

        # Player 3 (big blind) calls

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # The round should now be complete and advance to flop

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP, current_player_id=PLAYER_2))

        assert len(test.state.community_cards) == 3

    def test_all_in_affects_minimum_raise(self) -> None:
        """Test how all-in affects minimum raise calculations."""

        test = PokerTest.create(num_players=3, chips={PLAYER_1: 25})

        # Player 1 goes all-in with 25 chips (15 more than big blind)

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=25, current_player_id=PLAYER_2))

        # Player 2 should be able to raise, minimum raise should be to 40 (25 + 15)

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=40)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=40, current_player_id=PLAYER_3))

    def test_betting_round_transition_with_all_in(self) -> None:
        """Test betting round transitions when players are all-in."""

        test = PokerTest.create(num_players=3)

        # Player 1 goes all-in

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_2))

        # Player 2 calls the all-in

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_3))

        # Player 3 folds

        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)

        # Should advance to showdown since only one active player remains (player 2)

        # and one all-in player (player 1) - no more betting possible

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.SHOWDOWN))

        assert len(test.state.community_cards) == 5  # All community cards dealt

    def test_raise_after_multiple_calls(self) -> None:
        """Test raise after multiple players have called."""

        test = PokerTest.create(num_players=4)

        # Player 1 calls (first to act)

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_2))

        # Player 2 calls

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_3))

        # Player 3 calls

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_4))

        # Player 4 (big blind) raises

        test.process_move(PLAYER_4, TexasHoldemAction.RAISE, amount=40)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=40, current_player_id=PLAYER_1))

        # Action should return to player 1
        assert test.state.current_player_id == PLAYER_1

    def test_cap_betting_with_multiple_raises(self) -> None:
        """Test scenario with maximum number of raises in a round."""

        test = PokerTest.create(num_players=2, chips={PLAYER_1: 5000, PLAYER_2: 5000})

        # Player 1 raises to 50

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=50)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=50, current_player_id=PLAYER_2))

        # Player 2 re-raises to 150

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=150)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=150, current_player_id=PLAYER_1))

        # Player 1 re-raises to 450

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=450)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=450, current_player_id=PLAYER_2))

        # Player 2 re-raises to 1350

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=1350)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=1350, current_player_id=PLAYER_1))

    def test_betting_round_with_check_raise(self) -> None:
        """Test check-raise scenario in post-flop betting."""

        test = PokerTest.create(num_players=3)

        # Complete preflop with all calls

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)  # Big blind can check

        # Now in flop betting round

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP, current_player_id=PLAYER_2))

        # Player 2 (first to act post-flop) checks

        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

        # Player 3 bets

        test.process_move(PLAYER_3, TexasHoldemAction.RAISE, amount=20)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=20, current_player_id=PLAYER_1))

        # Player 1 folds

        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)

        # Player 2 check-raises

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=60)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=60, current_player_id=PLAYER_3))

        # Action should return to player 3 (since player_3 bet and player_2 raised)
        assert test.state.current_player_id == PLAYER_3

    def test_minimum_raise_with_fractional_all_in(self) -> None:
        """Test minimum raise calculation when previous 'raise' was actually a fractional all-in."""

        test = PokerTest.create(num_players=3, chips={PLAYER_1: 15})

        # Player 1 goes all-in with 15 chips (only 5 more than big blind of 10)

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=15, current_player_id=PLAYER_2))

        # Player 2 wants to raise, minimum raise should be to 25 (15 + 10)

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=25)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=25, current_player_id=PLAYER_3))
