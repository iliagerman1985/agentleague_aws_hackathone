"""Integration tests for complete Texas Hold'em game scenarios."""

from texas_holdem import BettingRound, Card, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PLAYER_5, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestIntegration:
    """Test complete game scenarios from start to finish."""

    def test_complete_game_all_check_to_showdown(self) -> None:
        """Test a complete game where all players check to showdown."""
        test = PokerTest.create(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("As")],
                PLAYER_2: [Card.of("Kh"), Card.of("Ks")],
                PLAYER_3: [Card.of("Qc"), Card.of("10d")],
                PLAYER_4: [Card.of("Jh"), Card.of("9s")],
                PLAYER_5: [Card.of("8c"), Card.of("7d")],
            }
        )

        # Complete preflop with all calls/checks
        # In 5-player game: P1=dealer, P2=SB, P3=BB, action starts with P4
        test.process_move(PLAYER_4, TexasHoldemAction.CALL)
        test.process_move(PLAYER_5, TexasHoldemAction.CALL)
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # Flop - all check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_5, TexasHoldemAction.CHECK)

        # Turn - all check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.TURN))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_5, TexasHoldemAction.CHECK)

        # River - all check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.RIVER))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_5, TexasHoldemAction.CHECK)

        # Game should be finished at showdown
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.SHOWDOWN,
                is_finished=True,
                winners=[PLAYER_1],  # Pair of Aces should win
            )
        )

    def test_complete_game_with_betting_action(self) -> None:
        """Test a complete game with significant betting action."""
        test = PokerTest.create()

        # Preflop action: raises and calls - PLAYER_1 acts first
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.process_move(PLAYER_4, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)

        # Players need to respond to the all-in
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.PREFLOP))

        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)

        # Game should end with PLAYER_4 winning
        test.assert_state_change(TexasHoldemStateDiff(is_finished=True, winners=[PLAYER_4]))

    def test_complete_game_early_fold_out(self) -> None:
        """Test game ending early when all but one player fold."""
        test = PokerTest.create()

        # PLAYER_1 raises big
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=100)

        # Everyone else folds
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_4, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)

        # Game should end immediately with PLAYER_1 winning
        test.assert_state_change(TexasHoldemStateDiff(is_finished=True, winners=[PLAYER_1]))

    def test_complete_game_all_in_showdown(self) -> None:
        """Test game with all-in players going to showdown."""
        test = PokerTest.create(
            num_players=3,
            chips={PLAYER_1: 50, PLAYER_2: 75, PLAYER_3: 100},
            hole_cards={PLAYER_1: [Card.of("Ah"), Card.of("As")], PLAYER_2: [Card.of("Kh"), Card.of("Ks")], PLAYER_3: [Card.of("Qh"), Card.of("Js")]},
        )

        # All players go all-in preflop
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)

        # Game should proceed directly to showdown since all players are all-in
        test.assert_state_change(
            TexasHoldemStateDiff(
                is_finished=True,
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.ALL_IN),
                    PLAYER_2: TexasHoldemPlayerDiff(status=PlayerStatus.ALL_IN),
                    PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.ALL_IN),
                },
                winners=[PLAYER_1],  # Pair of Aces should win
            )
        )

    def test_heads_up_complete_game(self) -> None:
        """Test a complete heads-up game."""
        test = PokerTest.create(num_players=2)

        # Preflop: small blind calls, big blind checks
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

        # Flop: big blind checks, small blind bets, big blind calls
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP))
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=20)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        # Turn: both check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.TURN))
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)

        # River: big blind bets, small blind folds
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.RIVER))
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=40)
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)

        # Game should end with PLAYER_2 winning
        test.assert_state_change(TexasHoldemStateDiff(is_finished=True, winners=[PLAYER_2]))

    def test_multiple_betting_rounds_with_raises(self) -> None:
        """Test game with multiple raises in different rounds."""
        test = PokerTest.create()

        # Preflop: raise, re-raise, call, call, call
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=60)
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.process_move(PLAYER_4, TexasHoldemAction.CALL)
        test.process_move(PLAYER_5, TexasHoldemAction.CALL)
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        # Flop: check, bet, raise, all-in, folds
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.RAISE, amount=40)
        test.process_move(PLAYER_4, TexasHoldemAction.RAISE, amount=80)
        test.process_move(PLAYER_5, TexasHoldemAction.ALL_IN)

        # After all-in, other players need to respond
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP))

        # Players fold to the all-in
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_4, TexasHoldemAction.FOLD)

        # Game should be over with PLAYER_5 winning
        test.assert_state_change(TexasHoldemStateDiff(is_finished=True, winners=[PLAYER_5]))

    def test_position_rotation_multiple_hands(self) -> None:
        """Test that positions are set correctly for different player counts."""
        # Test with 3 players
        test = PokerTest.create(num_players=3)
        assert 0 <= test.state.dealer_position < 3
        assert 0 <= test.state.small_blind_position < 3
        assert 0 <= test.state.big_blind_position < 3

        # Test with 4 players
        test = PokerTest.create(num_players=4)
        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_1  # First to act after big blind
            )
        )
        assert 0 <= test.state.dealer_position < 4
        assert 0 <= test.state.small_blind_position < 4
        assert 0 <= test.state.big_blind_position < 4

        # Test with 5 players (default)
        test = PokerTest.create()
        assert 0 <= test.state.dealer_position < 5
        assert 0 <= test.state.small_blind_position < 5
        assert 0 <= test.state.big_blind_position < 5

    def test_showdown_hand_evaluation(self) -> None:
        """Test proper hand evaluation at showdown."""
        test = PokerTest.create(
            num_players=3,
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("10h")],  # Flush (hearts)
                PLAYER_2: [Card.of("6c"), Card.of("7d")],  # Straight (6-7 with community 8-9-5)
                PLAYER_3: [Card.of("8s"), Card.of("9c")],  # Two pair (8s and 9s)
            },
            community_cards=[
                Card.of("8h"),  # Pairs with PLAYER_3's 8
                Card.of("9h"),  # Pairs with PLAYER_3's 9, helps PLAYER_2's straight
                Card.of("5h"),  # Helps PLAYER_1's flush, PLAYER_2's straight
                Card.of("4s"),  # Helps PLAYER_2's straight
                Card.of("3h"),  # Completes PLAYER_1's flush
            ],
            betting_round=BettingRound.RIVER,
        )

        # Play to showdown quickly - all call/check
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # Flop - all check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # Turn - all check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.TURN))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # River - all check
        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.RIVER))
        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # Game should now be over and PLAYER_1 should win with flush
        test.assert_state_change(
            TexasHoldemStateDiff(
                is_finished=True,
                winners=[PLAYER_1],  # Flush beats straight and two pair
            )
        )
