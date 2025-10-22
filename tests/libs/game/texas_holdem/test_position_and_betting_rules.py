"""Tests for position management and betting rules in Texas Hold'em.

Covers the different position rules between heads-up and multi-player games,
as well as comprehensive betting logic including minimum raises, all-ins, and edge cases.
"""

from texas_holdem import BettingRound, PlayerStatus, TexasHoldemAction
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestPositionAndBettingRules:
    """Test position management and betting rules comprehensively."""

    def test_heads_up_position_rules_preflop(self) -> None:
        """Test heads-up position rules: dealer is SB and acts first preflop."""
        test = PokerTest.create(num_players=2)

        # Verify initial positions
        assert test.state.dealer_position == 1
        assert test.state.small_blind_position == 1  # Dealer is SB in heads-up
        assert test.state.big_blind_position == 0
        assert test.state.current_player_id == PLAYER_2  # SB acts first preflop

        # SB calls (completes to BB)
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=20,
                current_player_id=PLAYER_1,
                action_position=0,
            ),
        )

        # BB can check or raise
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(current_bet=0),
                    PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                },
            ),
            exclude_fields={"community_cards", "deck", "current_player_id", "action_position"},
        )

    def test_heads_up_position_rules_postflop(self) -> None:
        """Test heads-up position rules: BB acts first postflop."""
        test = PokerTest.create(num_players=2, betting_round=BettingRound.FLOP, current_bet=0)

        # BB should act first postflop
        assert test.state.current_player_id == PLAYER_2  # BB
        assert test.state.action_position == 1

        # BB checks
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.CHECK,
            expected_state_diff=TexasHoldemStateDiff(
                current_player_id=PLAYER_1,  # Action moves to SB/Dealer
                action_position=0,
            ),
        )

        # SB can check or bet
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=20,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=980, current_bet=20, total_bet=20)},
                pot=25,
                current_bet=20,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=20,
                last_raise_position=0,
            ),
        )

    def test_multi_player_position_rules_preflop(self) -> None:
        """Test multi-player position rules: UTG acts first preflop."""
        test = PokerTest.create(num_players=4)

        # Verify initial positions
        assert test.state.dealer_position == 1
        assert test.state.small_blind_position == 2
        assert test.state.big_blind_position == 3
        assert test.state.action_position == 0  # UTG
        assert test.state.current_player_id == PLAYER_1  # UTG

        # UTG acts first
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=25,
                current_player_id=PLAYER_2,  # Dealer
                action_position=1,
            ),
        )

        # Action continues around the table
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)  # Dealer
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)  # SB
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)  # BB

        # Should advance to flop with SB acting first
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_player_id=PLAYER_3,  # SB acts first postflop
                action_position=2,
            ),
            exclude_fields={"community_cards", "deck", "players", "current_bet", "last_raise_amount"},
        )

    def test_multi_player_position_rules_postflop(self) -> None:
        """Test multi-player position rules: First active player acts first postflop."""
        test = PokerTest.create(num_players=4, betting_round=BettingRound.FLOP, current_bet=0)

        # First active player should act first postflop
        assert test.state.current_player_id == PLAYER_1  # First active player
        assert test.state.action_position == 0

        # If first player folds, action should skip to next active player
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_2,  # Next active player
                action_position=1,
            )
        )

    def test_minimum_raise_validation_comprehensive(self) -> None:
        """Test comprehensive minimum raise validation in different scenarios."""
        test = PokerTest.create(num_players=3)

        # Initial raise must be at least BB
        _ = test.process_move_error(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=15,  # Only 5 more than BB
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid initial raise
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=20,  # 10 more than BB
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=980, current_bet=20, total_bet=20)},
                current_bet=20,
                last_raise_amount=10,
                last_raise_position=0,
                current_player_id=PLAYER_2,
                action_position=1,
                pot=35,
            ),
        )

        # Re-raise must match previous raise amount
        _ = test.process_move_error(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=25,  # Only 5 more, but last raise was 10
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid re-raise
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=30,  # 10 more, matches last raise
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                current_bet=30,
                last_raise_position=1,
                current_player_id=PLAYER_3,
                action_position=2,
                pot=60,
            ),
        )

    def test_all_in_incomplete_raise_rules(self) -> None:
        """Test incomplete raise rules when player goes all-in below minimum raise."""
        test = PokerTest.create(chips={PLAYER_1: 15, PLAYER_2: 1000, PLAYER_3: 1000})

        # Player 1 goes all-in with 15 chips (incomplete raise - only 5 more than BB)
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.ALL_IN,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=15, total_bet=15, status=PlayerStatus.ALL_IN)},
                current_bet=15,
                last_raise_position=0,
                current_player_id=PLAYER_2,
                action_position=1,
                pot=30,
            ),
        )

        # Next player can still raise by the full minimum (BB = 10)
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=25,  # 15 + 10 = 25
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=975, current_bet=25, total_bet=25)},
                current_bet=25,
                last_raise_amount=10,  # Now it's a full raise
                last_raise_position=1,
                current_player_id=PLAYER_3,
                action_position=2,
                pot=55,
            ),
        )

    def test_all_in_complete_raise_rules(self) -> None:
        """Test complete raise rules when all-in meets minimum raise requirement."""
        test = PokerTest.create(chips={PLAYER_1: 25, PLAYER_2: 1000, PLAYER_3: 1000})

        # Player 1 goes all-in with 25 chips (complete raise - 15 more than BB)
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.ALL_IN,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=25, total_bet=25, status=PlayerStatus.ALL_IN)},
                current_bet=25,
                last_raise_amount=15,  # Complete raise updates last_raise_amount
                last_raise_position=0,
                current_player_id=PLAYER_2,
                action_position=1,
                pot=40,
            ),
        )

        # Next player must raise by at least 15 to re-raise
        _ = test.process_move_error(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=35,  # Only 10 more
            expected_error=THErrors.RAISE_TOO_SMALL,
        )

        # Valid re-raise
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=40,  # 15 more
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=960, current_bet=40, total_bet=40)},
                current_bet=40,
                last_raise_position=1,
                current_player_id=PLAYER_3,
                action_position=2,
                pot=80,
            ),
        )

    def test_insufficient_chips_scenarios(self) -> None:
        """Test various insufficient chip scenarios."""
        test = PokerTest.create(chips={PLAYER_1: 8, PLAYER_2: 1000, PLAYER_3: 1000})

        # Player with insufficient chips for call goes all-in
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.CALL,
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=8, total_bet=8, status=PlayerStatus.ALL_IN)},
                pot=23,  # 5 (SB) + 10 (BB) + 8 (all-in)
                current_player_id=PLAYER_2,
                action_position=1,
            ),
        )

        # Player with insufficient chips for raise goes all-in
        test = PokerTest.create(chips={PLAYER_1: 25, PLAYER_2: 1000, PLAYER_3: 1000})
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)  # Wants to raise to 30
        test.process_move(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=50,  # Wants to raise to 50 but only has 25 left
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=950, current_bet=50, total_bet=50)},
                current_bet=50,
                current_player_id=PLAYER_3,
                action_position=2,
                pot=90,
                last_raise_amount=25,
                last_raise_position=1,
            ),
        )

    def test_betting_round_completion_logic(self) -> None:
        """Test the logic for when betting rounds complete."""
        test = PokerTest.create(num_players=3)

        # Raise, call, call should complete the round
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        # Before the last call, round should not be complete
        assert test.get_betting_round() == BettingRound.PREFLOP

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # After last call, should advance to flop
        test.assert_state_change(
            TexasHoldemStateDiff(betting_round=BettingRound.FLOP),
            exclude_fields={"community_cards", "deck", "players", "current_player_id", "action_position", "current_bet", "last_raise_amount", "pot"},
        )

    def test_action_skipping_inactive_players(self) -> None:
        """Test that action correctly skips folded and all-in players."""
        test = PokerTest.create(num_players=4)

        # In 4-player game: UTG=0 (PLAYER_1), dealer=1 (PLAYER_2), SB=2 (PLAYER_3), BB=3 (PLAYER_4)
        # UTG (Player 1) acts first, then dealer (Player 2), then SB (Player 3), then BB (Player 4)

        # UTG (Player 1) folds
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)

        # Dealer (Player 2) goes all-in
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)

        # SB (Player 3) calls
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # Action should go to BB (Player 4), skipping the folded and all-in players
        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_4),
            exclude_fields={"players", "pot", "current_bet", "last_raise_amount", "last_raise_position", "action_position"},
        )

        test.process_move(PLAYER_4, TexasHoldemAction.CALL)

        # Should advance to flop, and action should start with SB (Player 3) since others are folded/all-in
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_player_id=PLAYER_3,  # Only active player left
                pot=3000,
            ),
            exclude_fields={"community_cards", "deck", "players", "current_bet", "action_position", "last_raise_amount"},
        )

    def test_max_raise_validation(self) -> None:
        """Test maximum raise validation when configured."""
        test = PokerTest.create(max_raise=100)

        # Raise within limit should work
        test.process_move(
            PLAYER_1,
            TexasHoldemAction.RAISE,
            amount=110,  # 100 more than current bet
            expected_state_diff=TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=890, current_bet=110, total_bet=110)},
                current_bet=110,
                current_player_id=PLAYER_2,
                action_position=1,
                pot=125,
                last_raise_amount=100,
                last_raise_position=0,
            ),
        )

        # Raise exceeding limit should fail
        _ = test.process_move_error(
            PLAYER_2,
            TexasHoldemAction.RAISE,
            amount=220,  # 110 more than current bet, exceeds max_raise of 100
            expected_error=THErrors.RAISE_TOO_LARGE,
        )
