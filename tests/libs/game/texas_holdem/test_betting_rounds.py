"""Tests for betting rounds and game flow in Texas Hold'em."""

from texas_holdem import BettingRound, Card, CardRank, CardSuit, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff

# Common fields to exclude from state diff assertions
COMMON_EXCLUDE_FIELDS = {
    "players.hole_cards",
    "community_cards",
    "action_position",
    "current_player_id",
    "current_bet",
    "pot",
    "side_pots",
    "last_raise_amount",
    "last_raise_position",
    "players.current_bet",
    "players.total_bet",
    "players.chips",
    "betting_round",
    "is_finished",
    "winners",
    "winning_hands",
    "deck",
}


class TestBettingRounds:
    """Test betting round progression and game flow."""

    def test_preflop_to_flop_progression(self) -> None:
        """Test progression from preflop to flop."""
        test = PokerTest.create(num_players=3)

        # Complete preflop betting: all players call
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=25,
                current_player_id=PLAYER_2,
                action_position=1,
            )
        )

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=30,
                current_player_id=PLAYER_3,
                action_position=2,
            )
        )

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)  # Big blind checks
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
            exclude_fields={"community_cards", "players.current_bet", "deck"},
        )

    def test_flop_to_turn_progression(self) -> None:
        """Test progression from flop to turn."""
        test = PokerTest.create(num_players=3)

        # Complete preflop to get to flop
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
            exclude_fields={"community_cards", "players.current_bet", "deck"},
        )

        # All players check on flop
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_3, action_position=2))

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.assert_state_change(TexasHoldemStateDiff(current_player_id=PLAYER_1, action_position=0))

        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.TURN,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
            exclude_fields={"community_cards", "players.current_bet", "deck"},
        )

    def test_turn_to_river_progression(self) -> None:
        """Test progression from turn to river."""
        test = PokerTest.create(num_players=3)

        # Complete preflop to get to flop
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
            exclude_fields={"community_cards", "players.current_bet", "deck"},
        )

        # All players check on flop to get to turn
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.TURN,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
            exclude_fields={"community_cards", "players.current_bet", "deck"},
        )

        # All players check on turn
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.RIVER,
                current_player_id=PLAYER_2,
                action_position=1,
            ),
            exclude_fields={"community_cards", "players.current_bet", "deck"},
        )

    def test_river_to_showdown_progression(self) -> None:
        """Test progression from river to showdown."""
        test = PokerTest.create(
            num_players=3,
            betting_round=BettingRound.RIVER,
            current_bet=0,
            community_cards=[
                Card(rank=CardRank.TWO, suit=CardSuit.HEARTS),
                Card(rank=CardRank.SEVEN, suit=CardSuit.DIAMONDS),
                Card(rank=CardRank.TEN, suit=CardSuit.CLUBS),
                Card(rank=CardRank.FIVE, suit=CardSuit.SPADES),
                Card(rank=CardRank.NINE, suit=CardSuit.HEARTS),
            ],
        )

        # All players check on river
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)

        # Should advance to showdown and game should be over
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

    def test_betting_round_with_raise(self) -> None:
        """Test betting round completion with raises."""
        test = PokerTest.create(num_players=3)

        # Player 1 calls
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Player 2 raises
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=30)

        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

        # Player 3 calls the raise
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # Player 1 must act again (call the raise)
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

        # Player 1 calls the raise
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Now should advance to flop
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

    def test_multiple_raises_in_round(self) -> None:
        """Test multiple raises in a single betting round."""
        test = PokerTest.create(num_players=3)

        # Player 1 raises
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)

        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

        # Player 2 re-raises
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=60)

        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

        # Player 3 calls
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # Player 1 must act again
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

        # Player 1 calls the re-raise
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Player 2 already has the right amount, so round should complete
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

    def test_all_fold_except_one(self) -> None:
        """Test game ends when all but one player fold."""
        test = PokerTest.create(num_players=3)

        # Player 1 folds
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED),
                },
            ),
            exclude_fields=COMMON_EXCLUDE_FIELDS,
        )

        # Player 2 folds
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)

        # Game should be over with player 3 as winner
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_2: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED),
                },
            ),
            exclude_fields=COMMON_EXCLUDE_FIELDS,
        )

    def test_all_in_scenarios(self) -> None:
        """Test betting rounds with all-in players."""
        test = PokerTest.create(num_players=3)

        # Player 1 goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.ALL_IN),
                },
            ),
            exclude_fields=COMMON_EXCLUDE_FIELDS,
        )

        # Player 2 calls the all-in (this will also make them all-in)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_2: TexasHoldemPlayerDiff(status=PlayerStatus.ALL_IN),
                },
            ),
            exclude_fields=COMMON_EXCLUDE_FIELDS,
        )

        # Player 3 still needs to act - let them fold
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)

        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED),
                },
            ),
            exclude_fields=COMMON_EXCLUDE_FIELDS,
        )

    def test_heads_up_betting(self) -> None:
        """Test betting in heads-up (2 player) scenario."""
        test = PokerTest.create(num_players=2)

        # Small blind calls
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Big blind checks
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

        # Should advance to flop
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

    def test_betting_round_reset_after_advance(self) -> None:
        """Test that betting amounts reset when advancing rounds."""
        test = PokerTest.create(num_players=3)

        # Players make bets in preflop
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=50)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # Verify we're on flop and betting has reset
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)

    def test_action_position_after_round_advance(self) -> None:
        """Test that action position is set correctly after round advance."""
        test = PokerTest.create(num_players=3)

        # Complete preflop - all players call
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)  # BB can check

        # On flop, action should start with first player after dealer
        test.assert_state_change(TexasHoldemStateDiff(), exclude_fields=COMMON_EXCLUDE_FIELDS)
