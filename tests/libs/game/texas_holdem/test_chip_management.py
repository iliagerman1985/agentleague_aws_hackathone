"""Tests for chip management in Texas Hold'em."""

from texas_holdem import BettingRound, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestChipManagement:
    """Test chip management and stack handling."""

    def test_basic_round(self) -> None:
        """Test a basic round."""
        test = PokerTest.create(num_players=3)

        # Make some moves
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=45,
                current_bet=30,
                current_player_id=PLAYER_2,
                last_raise_amount=30,
                last_raise_position=0,
                action_position=1,
            )
        )

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=70,
                current_player_id=PLAYER_3,
                action_position=2,
            )
        )

        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_1,
            )
        )

        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)
        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                current_player_id=PLAYER_2,
            ),
            exclude_fields={"community_cards"},
        )

    def test_exact_chip_amount_scenarios(self) -> None:
        """Test scenarios with exact chip amounts."""
        test = PokerTest.create(chips={PLAYER_2: 30})

        # Player 1 raises
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                pot=45,
                current_bet=30,
                current_player_id=PLAYER_2,
                last_raise_amount=30,
                last_raise_position=0,
                action_position=1,
            )
        )

        # Player 2 with exact amount can call (going all-in)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_2: TexasHoldemPlayerDiff(
                        chips=0,
                        current_bet=30,
                        total_bet=30,
                        status=PlayerStatus.ALL_IN,
                    )
                },
                pot=70,
                current_player_id=PLAYER_3,
                action_position=2,
            )
        )

    def test_chip_distribution_after_all_in(self) -> None:
        """Test chip distribution when players go all-in with different amounts."""
        test = PokerTest.create(num_players=4, chips={PLAYER_1: 25, PLAYER_2: 50, PLAYER_3: 75})

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=25, total_bet=25, status=PlayerStatus.ALL_IN)},
                current_bet=25,
                pot=40,
                current_player_id=PLAYER_2,
                last_raise_amount=15,
                last_raise_position=0,
                action_position=1,
            )
        )

        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=0, current_bet=50, total_bet=50, status=PlayerStatus.ALL_IN)},
                current_bet=50,
                pot=90,
                current_player_id=PLAYER_3,
                last_raise_amount=25,
                last_raise_position=1,
                action_position=2,
            )
        )

        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=0, current_bet=75, total_bet=75, status=PlayerStatus.ALL_IN)},
                current_bet=75,
                pot=165,
                current_player_id=PLAYER_1,
                last_raise_amount=25,
                last_raise_position=2,
                action_position=0,
            )
        )

        # Force to showdown
        test.advance_to_showdown()

        # Verify game completion and chip conservation
        test.assert_state_change(TexasHoldemStateDiff(is_finished=True))
        total_chips = sum(player.chips for player in test.state.players)
        initial_total = 25 + 50 + 75 + 1000  # Fourth player keeps default 1000
        assert total_chips == initial_total, f"Total chips should be {initial_total}, got {total_chips}"

    def test_negative_chip_prevention(self) -> None:
        """Test that players cannot have negative chips."""
        test = PokerTest.create(chips={PLAYER_1: 5})

        # Player 1 raises with more chips than available
        error = test.process_move_error(PLAYER_1, TexasHoldemAction.RAISE, amount=6)
        assert error is not None

    def test_chip_stack_edge_cases(self) -> None:
        """Test edge cases with chip stacks."""
        test = PokerTest.create(num_players=3, chips={PLAYER_2: 5, PLAYER_3: 10})  # Only enough for blinds

        # TODO: Assert on initial game state is as expected

        # Player 1 calls
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                current_player_id=PLAYER_2,
            )
        )

    def test_all_in_with_zero_chips(self) -> None:
        """Test all-in behavior when player has zero chips."""
        test = PokerTest.create(chips={PLAYER_3: 10})  # Big blind only has blind amount

        # Other players act
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # Verify big blind is all-in after posting blind
        test.assert_state_change(TexasHoldemStateDiff(players={PLAYER_3: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN)}))

    def test_chip_movement_tracking(self) -> None:
        """Test tracking of chip movements between players and pots."""
        test = PokerTest.create()

        # Record initial total for verification
        initial_total = test.get_total_chips_in_play()

        # Make moves and track changes
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=970, current_bet=30, total_bet=30)},
                current_player_id=PLAYER_2,
            )
        )

        # Total should still be conserved
        current_total = test.get_total_chips_in_play()
        assert current_total == initial_total

    def test_maximum_bet_with_available_chips(self) -> None:
        """Test maximum bet scenarios with available chips."""
        test = PokerTest.create()

        # Player bets all available chips
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, total_bet=1000, status=PlayerStatus.ALL_IN)},
                current_player_id=PLAYER_2,
            )
        )

    def test_partial_blind_scenarios(self) -> None:
        """Test scenarios where players can't post full blinds."""
        test = PokerTest.create(
            num_players=4,
            chips={PLAYER_2: 3, PLAYER_3: 7},  # Insufficient for full blinds
        )

        # Verify both players are all-in after posting partial blinds
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_2: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN),
                    PLAYER_3: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN),
                }
            )
        )

        # UTG should still be able to act
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

    def test_chip_consistency_across_rounds(self) -> None:
        """Test chip consistency across multiple betting rounds."""
        test = PokerTest.create()

        # Track chips through multiple rounds
        initial_total = test.get_total_chips_in_play()

        # Complete preflop
        test.process_move(PLAYER_1, TexasHoldemAction.CALL)
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # Check after preflop
        flop_total = test.get_total_chips_in_play()
        assert flop_total == initial_total

        # Make flop bets
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=20)
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

        # Check after flop
        turn_total = test.get_total_chips_in_play()
        assert turn_total == initial_total

    def test_side_pot_chip_distribution(self) -> None:
        """Test correct chip distribution in side pot scenarios."""
        test = PokerTest.create(
            num_players=4,
            chips={PLAYER_1: 20, PLAYER_2: 40, PLAYER_3: 60, PLAYER_4: 80},
        )

        # All go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_4, TexasHoldemAction.ALL_IN)

        # Force to showdown
        test.advance_to_showdown()

        # Verify chip conservation
        total_chips = sum(player.chips for player in test.state.players)
        initial_total = 20 + 40 + 60 + 80
        assert total_chips == initial_total, f"Total chips should be {initial_total}, got {total_chips}"

    def test_minimum_raise_with_limited_chips(self) -> None:
        """Test minimum raise requirements with limited chip stacks."""
        test = PokerTest.create(chips={PLAYER_2: 25})

        # UTG raises
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=20)

        # Player with limited chips goes all-in
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.assert_state_change(TexasHoldemStateDiff(players={PLAYER_2: TexasHoldemPlayerDiff(chips=0, total_bet=25, status=PlayerStatus.ALL_IN)}))

    def test_chip_overflow_prevention(self) -> None:
        """Test prevention of chip overflow in extreme scenarios."""
        test = PokerTest.create(chips={PLAYER_1: 1000000})

        # Make large bet
        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=100000)
        test.assert_state_change(TexasHoldemStateDiff(players={PLAYER_1: TexasHoldemPlayerDiff(chips=900000, current_bet=100000, total_bet=100000)}))
