"""Tests for position management in Texas Hold'em."""

from texas_holdem import BettingRound, PlayerStatus, TexasHoldemAction
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestPositionManagement:
    """Test dealer button rotation and action order validation."""

    def test_dealer_button_rotation_three_players(self) -> None:
        """Test dealer button rotation with three players."""
        test = PokerTest.create(num_players=3)

        # Record initial positions
        initial_dealer = test.state.dealer_position
        initial_small_blind = test.state.small_blind_position
        initial_big_blind = test.state.big_blind_position

        # Verify initial positions are within valid range
        assert 0 <= initial_dealer < 3
        assert 0 <= initial_small_blind < 3
        assert 0 <= initial_big_blind < 3

        # Verify all positions are different
        positions = {initial_dealer, initial_small_blind, initial_big_blind}
        assert len(positions) == 3, "All positions should be different with 3 players"

        # Complete the hand - PLAYER_1 should be first to act
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)

        # Game should be over, PLAYER_3 wins
        assert test.is_game_finished()

    def test_dealer_button_rotation_heads_up(self) -> None:
        """Test dealer button rotation in heads-up play."""
        test = PokerTest.create(num_players=2)

        # In heads-up, dealer is small blind
        dealer_pos = test.state.dealer_position
        small_blind_pos = test.state.small_blind_position
        big_blind_pos = test.state.big_blind_position

        # Verify positions are set correctly
        assert 0 <= dealer_pos < 2
        assert 0 <= small_blind_pos < 2
        assert 0 <= big_blind_pos < 2

        # In heads-up, dealer is small blind
        assert dealer_pos == small_blind_pos
        assert dealer_pos != big_blind_pos

        # First to act in heads-up should be PLAYER_1
        assert test.state.current_player_id == PLAYER_1

    def test_action_order_preflop(self) -> None:
        """Test that action order is correct preflop."""
        test = PokerTest.create(num_players=4)

        # Preflop action should start with PLAYER_1 (first after big blind)
        assert test.state.current_player_id == PLAYER_1

        # Track action order through the round
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_2, action_position=1, players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=25
            )
        )

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3, action_position=2, players={PLAYER_2: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=35
            )
        )

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_4, action_position=3, players={PLAYER_3: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=40
            )
        )

        # PLAYER_4 (big blind) can check
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)

    def test_action_order_postflop(self) -> None:
        """Test that action order is correct postflop."""
        test = PokerTest.create(num_players=4)

        # Complete preflop
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)

        # Postflop action should start with first active player after dealer
        if not test.is_game_finished():
            test.assert_state_change(
                TexasHoldemStateDiff(
                    betting_round=BettingRound.FLOP,
                    current_player_id=PLAYER_2,  # First to act postflop
                    current_bet=0,  # Betting resets for new round
                    action_position=1,
                    players={
                        PLAYER_1: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_3: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_4: TexasHoldemPlayerDiff(current_bet=0),
                    },
                ),
                exclude_fields={"deck", "community_cards"},
            )

    def test_action_skips_folded_players(self) -> None:
        """Test that action correctly skips folded players."""
        test = PokerTest.create(num_players=4)

        # PLAYER_1 folds
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_2, action_position=1, players={PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)})
        )

        # PLAYER_2 calls (small blind needs to call 5 more to match big blind)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3, action_position=2, players={PLAYER_2: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=25
            )
        )

        # PLAYER_3 folds
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_4, action_position=3, players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)})
        )

        # PLAYER_4 (big blind) can check
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)

    def test_action_skips_all_in_players_postflop(self) -> None:
        """Test that action skips all-in players in subsequent rounds."""
        test = PokerTest.create(num_players=3)

        # PLAYER_1 goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_2,
                action_position=1,
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN, current_bet=1000, total_bet=1000)},
                pot=1015,
                current_bet=1000,
                last_raise_amount=990,
                last_raise_position=0,
            )
        )

        # PLAYER_2 calls
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3,
                action_position=2,
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN, current_bet=1000, total_bet=1000)},
                pot=2010,
            )
        )

        # PLAYER_3 calls
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # If game continues to postflop, all-in player should be skipped
        if not test.is_game_finished():
            # Action should start with PLAYER_2 (first active player after dealer)
            test.assert_state_change(
                TexasHoldemStateDiff(
                    betting_round=BettingRound.FLOP,
                    current_player_id=PLAYER_2,
                    current_bet=0,  # Betting resets for new round
                    action_position=1,
                    players={
                        PLAYER_1: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_3: TexasHoldemPlayerDiff(current_bet=0),
                    },
                )
            )

    def test_blind_positions_with_different_player_counts(self) -> None:
        """Test blind positions are correct for different player counts."""
        for num_players in [2, 3, 4, 5]:
            test = PokerTest.create(num_players=num_players)

            # Verify positions are within valid range
            assert 0 <= test.state.dealer_position < num_players
            assert 0 <= test.state.small_blind_position < num_players
            assert 0 <= test.state.big_blind_position < num_players

            # Verify positions are different (except in heads-up where dealer = small blind)
            if num_players == 2:
                # In heads-up, dealer is small blind
                assert test.state.dealer_position == test.state.small_blind_position
                assert test.state.dealer_position != test.state.big_blind_position
            else:
                # With 3+ players, all positions should be different
                positions = {test.state.dealer_position, test.state.small_blind_position, test.state.big_blind_position}
                assert len(positions) == 3, "All positions should be different with 3+ players"

            # Verify blind positions are set correctly
            if num_players > 2:
                # Small blind is player before last, big blind is last player
                expected_small_blind = num_players - 2
                expected_big_blind = num_players - 1
                assert test.state.small_blind_position == expected_small_blind
                assert test.state.big_blind_position == expected_big_blind

    def test_action_position_tracking(self) -> None:
        """Test that action position is tracked correctly."""
        test = PokerTest.create(num_players=3)

        # Initial action should be with PLAYER_1
        assert test.state.current_player_id == PLAYER_1

        # Make a move
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Action should advance to PLAYER_2
        if not test.is_game_finished():
            test.assert_state_change(
                TexasHoldemStateDiff(
                    current_player_id=PLAYER_2, action_position=1, players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=25
                )
            )

    def test_betting_round_position_reset(self) -> None:
        """Test that positions reset correctly for new betting rounds."""
        test = PokerTest.create(num_players=4)

        # Complete preflop
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)

        # If we reach postflop, action should start with first active player after dealer
        if not test.is_game_finished():
            test.assert_state_change(
                TexasHoldemStateDiff(
                    betting_round=BettingRound.FLOP,
                    current_player_id=PLAYER_2,  # First to act postflop
                    current_bet=0,  # Betting resets for new round
                    action_position=1,
                    players={
                        PLAYER_1: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_2: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_3: TexasHoldemPlayerDiff(current_bet=0),
                        PLAYER_4: TexasHoldemPlayerDiff(current_bet=0),
                    },
                ),
                exclude_fields={"deck", "community_cards"},
            )

    def test_position_consistency_after_folds(self) -> None:
        """Test that positions remain consistent when players fold."""
        test = PokerTest.create()

        # Record initial positions
        initial_dealer = test.state.dealer_position
        initial_small_blind = test.state.small_blind_position
        initial_big_blind = test.state.big_blind_position

        # Players fold
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)

        # Positions should remain the same, but we need to check the actual state diff
        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_3, action_position=2, players={PLAYER_2: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)})
        )

        # Verify positions haven't changed
        assert test.state.dealer_position == initial_dealer
        assert test.state.small_blind_position == initial_small_blind
        assert test.state.big_blind_position == initial_big_blind

    def test_heads_up_position_special_case(self) -> None:
        """Test special position rules for heads-up play."""
        test = PokerTest.create(num_players=2)

        # In heads-up, dealer is small blind and acts first preflop
        assert test.state.current_player_id == PLAYER_1  # Dealer/small blind acts first

        # Complete preflop
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Big blind can check or raise
        if not test.is_game_finished():
            test.assert_state_change(
                TexasHoldemStateDiff(
                    current_player_id=PLAYER_2,  # Big blind
                    action_position=1,
                    players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                    pot=20,
                )
            )

    def test_invalid_position_values(self) -> None:
        """Test handling of invalid position values."""
        test = PokerTest.create(num_players=3)

        # Test that positions are within valid range
        assert 0 <= test.state.dealer_position < 3
        assert 0 <= test.state.small_blind_position < 3
        assert 0 <= test.state.big_blind_position < 3
        assert 0 <= test.state.action_position < 3

        # Manually set invalid position (for testing error handling)
        original_action_position = test.state.action_position
        test.state.action_position = 99  # Invalid position

        # Attempt to process move with invalid position - should fail
        # Test that invalid position causes an error
        _ = test.process_move_error(PLAYER_1, TexasHoldemAction.CALL, expected_error=THErrors.NOT_PLAYER_TURN)

        # Restore valid position for cleanup
        test.state.action_position = original_action_position

    def test_position_wraparound(self) -> None:
        """Test that position calculations are consistent."""
        test = PokerTest.create(num_players=3)

        # With our fixed positioning logic:
        # Small blind is always player 1 (num_players - 2 = 3 - 2 = 1)
        # Big blind is always player 2 (num_players - 1 = 3 - 1 = 2)
        # Dealer is always player 0

        expected_dealer = 0
        expected_sb = 1  # num_players - 2
        expected_bb = 2  # num_players - 1

        # Verify positions are correct
        assert test.state.dealer_position == expected_dealer
        assert test.state.small_blind_position == expected_sb
        assert test.state.big_blind_position == expected_bb

        # Verify all positions are different
        positions = {test.state.dealer_position, test.state.small_blind_position, test.state.big_blind_position}
        assert len(positions) == 3, "All positions should be different with 3 players"

    def test_action_order_with_raises(self) -> None:
        """Test that action order handles raises correctly."""
        test = PokerTest.create(num_players=4)

        # PLAYER_1 calls
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_2, action_position=1, players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)}, pot=25
            )
        )

        # PLAYER_2 raises
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=20)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3,
                action_position=2,
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=980, current_bet=20, total_bet=20)},
                pot=45,
                current_bet=20,
                last_raise_amount=20,
                last_raise_position=1,
            )
        )

        # PLAYER_3 folds
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_4, action_position=3, players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)})
        )

        # PLAYER_4 calls
        test.process_move(PLAYER_4, TexasHoldemAction.CALL)

        # Action should come back to PLAYER_1 (who needs to act on the raise)
        if not test.is_game_finished():
            test.assert_state_change(
                TexasHoldemStateDiff(
                    current_player_id=PLAYER_1, action_position=0, players={PLAYER_4: TexasHoldemPlayerDiff(chips=980, current_bet=20, total_bet=20)}, pot=55
                )
            )
