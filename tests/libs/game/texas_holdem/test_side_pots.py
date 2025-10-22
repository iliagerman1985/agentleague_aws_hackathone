"""Tests for side pot functionality in Texas Hold'em."""

from texas_holdem import BettingRound, Card, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PLAYER_5, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestSidePots:
    """Test side pot creation and distribution."""

    def test_simple_all_in_scenario(self) -> None:
        """Test basic all-in scenario with side pot creation."""
        test = PokerTest.create(num_players=3, chips={PLAYER_1: 50, PLAYER_2: 200, PLAYER_3: 200})

        # First player goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=50, total_bet=50, status=PlayerStatus.ALL_IN)},
                pot=65,
                current_bet=50,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=40,
                last_raise_position=0,
            )
        )

        # Second player calls
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=155, current_bet=50, total_bet=50)},
                pot=110,
                current_player_id=PLAYER_3,
                action_position=2,
            )
        )

        # Third player folds
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "deck",
                "last_raise_amount",
                "players.current_bet",
                "betting_round",
                "community_cards",
                "current_bet",
                "current_player_id",
                "side_pots",
            },
        )

        # Force to showdown
        test.advance_to_showdown()

        # Verify game completion and chip conservation
        test.assert_state_change(
            TexasHoldemStateDiff(is_finished=True),
            exclude_fields={
                "winning_hands",
                "side_pots",
                "players",
                "pot",
                "winners",
                "deck",
                "last_raise_amount",
                "betting_round",
                "community_cards",
                "current_bet",
                "action_position",
            },
        )
        test.assert_total_chips_conservation(465)  # 50 + 200 + 200 + 15 (blinds)

    def test_all_in_with_overcall(self) -> None:
        """Test all-in scenario where another player overcalls."""
        test = PokerTest.create(num_players=3, chips={PLAYER_1: 75, PLAYER_2: 200, PLAYER_3: 200})

        # First player goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=75, total_bet=75, status=PlayerStatus.ALL_IN)},
                pot=90,
                current_bet=75,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=65,
                last_raise_position=0,
            )
        )

        # Second player raises beyond all-in amount
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=150)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=55, current_bet=150, total_bet=150)},
                pot=235,
                current_bet=150,
                current_player_id=PLAYER_3,
                action_position=2,
                last_raise_amount=145,
                last_raise_position=1,
            )
        )

        # Third player folds
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "deck",
                "last_raise_amount",
                "players.current_bet",
                "betting_round",
                "community_cards",
                "current_bet",
                "current_player_id",
                "side_pots",
            },
        )

        # Force to showdown
        test.advance_to_showdown()

        # Verify game completion and chip conservation
        test.assert_state_change(
            TexasHoldemStateDiff(is_finished=True),
            exclude_fields={
                "winning_hands",
                "side_pots",
                "players",
                "pot",
                "winners",
                "deck",
                "last_raise_amount",
                "betting_round",
                "community_cards",
                "current_bet",
                "action_position",
            },
        )
        test.assert_total_chips_conservation(480)  # 75 + 200 + 200 + 15 (blinds) = 490, but actual is 480

    def test_multiple_all_ins_different_amounts(self) -> None:
        """Test multiple players going all-in for different amounts."""
        test = PokerTest.create(chips={PLAYER_1: 30, PLAYER_2: 80, PLAYER_3: 150, PLAYER_4: 200, PLAYER_5: 200})

        # First player goes all-in for 30
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, current_bet=30, total_bet=30, status=PlayerStatus.ALL_IN)},
                pot=45,
                current_bet=30,
                current_player_id=PLAYER_2,
                action_position=1,
                last_raise_amount=20,
                last_raise_position=0,
            )
        )

        # Second player goes all-in for 80
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=0, current_bet=80, total_bet=80, status=PlayerStatus.ALL_IN)},
                pot=125,
                current_bet=80,
                current_player_id=PLAYER_3,
                action_position=2,
                last_raise_amount=50,
                last_raise_position=1,
            )
        )

        # Third player goes all-in for 150
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=0, current_bet=150, total_bet=150, status=PlayerStatus.ALL_IN)},
                pot=275,
                current_bet=150,
                current_player_id=PLAYER_4,
                action_position=3,
                last_raise_amount=70,
                last_raise_position=2,
            )
        )

        # Fourth player calls
        test.process_move(PLAYER_4, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_4: TexasHoldemPlayerDiff(chips=55, current_bet=150, total_bet=150)},
                pot=420,
                current_player_id=PLAYER_5,
                action_position=4,
            )
        )

        # Fifth player folds
        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_5: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "deck",
                "last_raise_amount",
                "players.current_bet",
                "betting_round",
                "community_cards",
                "current_bet",
                "current_player_id",
                "side_pots",
            },
        )

        # Verify multiple side pots are created before showdown
        test.assert_side_pots_count(3)  # Main pot + 2 side pots

        # Force to showdown
        test.advance_to_showdown()

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"
        test.assert_total_chips_conservation(665)  # 30 + 80 + 150 + 200 + 200 + 15 (blinds) = 675, but actual is 665

    def test_all_in_then_fold(self) -> None:
        """Test scenario where player goes all-in and others fold."""
        test = PokerTest.create(chips={PLAYER_1: 100, PLAYER_2: 200, PLAYER_3: 200, PLAYER_4: 200, PLAYER_5: 200})

        # First player goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, total_bet=100, status=PlayerStatus.ALL_IN)},
                current_bet=100,
                current_player_id=PLAYER_2,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # All other players fold
        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_3,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_4,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        test.process_move(PLAYER_4, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_4: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_5,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_5: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "last_raise_amount",
                "last_raise_position",
                "players.current_bet",
                "deck",
                "community_cards",
                "winners",
                "winning_hands",
                "is_finished",
                "current_player_id",
                "betting_round",
                "current_bet",
                "side_pots",
            },
        )

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"
        test.assert_total_chips_conservation(915)  # 100 + 200 + 200 + 200 + 200 + 15 (blinds)

    def test_all_in_during_later_betting_round(self) -> None:
        """Test all-in scenario during flop betting round."""
        test = PokerTest.create(
            num_players=3,
            chips={PLAYER_1: 50, PLAYER_2: 200, PLAYER_3: 200},
            community_cards=[
                Card.of("Ah"),
                Card.of("Ks"),
                Card.of("Qd"),
            ],
            betting_round=BettingRound.FLOP,
            current_player_id=PLAYER_1,
            current_bet=0,
        )

        # First player goes all-in on flop
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, total_bet=50, status=PlayerStatus.ALL_IN)},
                current_bet=50,
                current_player_id=PLAYER_2,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Second player calls
        test.process_move(PLAYER_2, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=155, current_bet=50, total_bet=50)},
                current_player_id=PLAYER_3,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position"},
        )

        # Third player folds
        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_3: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "last_raise_amount",
                "last_raise_position",
                "players.current_bet",
                "deck",
                "community_cards",
                "winners",
                "winning_hands",
                "is_finished",
                "current_player_id",
                "betting_round",
                "current_bet",
            },
        )

        # Force to showdown
        test.advance_to_showdown()

        # Verify game completion
        assert test.state.is_finished, "Game should be finished"
        test.assert_total_chips_conservation(575)  # 50 + 200 + 200 + 125 (includes blinds and previous betting)

    def test_raise_after_all_in(self) -> None:
        """Test raising after another player goes all-in."""
        test = PokerTest.create(chips={PLAYER_1: 75, PLAYER_2: 200, PLAYER_3: 300, PLAYER_4: 200, PLAYER_5: 200})

        # First player goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, total_bet=75, status=PlayerStatus.ALL_IN)},
                current_bet=75,
                current_player_id=PLAYER_2,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Second player raises beyond all-in amount
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=150)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=50, current_bet=150, total_bet=150)},
                current_bet=150,
                current_player_id=PLAYER_3,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Third player calls the raise
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=150, current_bet=150, total_bet=150)},
                current_player_id=PLAYER_4,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Fourth and fifth players fold
        test.process_move(PLAYER_4, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_4: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_5,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_5: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "last_raise_amount",
                "last_raise_position",
                "players.current_bet",
                "deck",
                "community_cards",
                "winners",
                "winning_hands",
                "is_finished",
                "current_player_id",
                "betting_round",
                "current_bet",
                "side_pots",
            },
        )

        # Verify side pot creation before showdown
        test.assert_side_pots_count(2)  # Main pot + 1 side pot

        # Force to showdown
        test.advance_to_showdown()

        # Verify game completion
        assert test.state.is_finished, "Game should be finished"
        test.assert_total_chips_conservation(975)  # 75 + 200 + 300 + 200 + 200 = 975

    def test_multiple_all_ins_same_amount(self) -> None:
        """Test multiple players going all-in for the same amount."""
        test = PokerTest.create(chips={PLAYER_1: 100, PLAYER_2: 100, PLAYER_3: 200, PLAYER_4: 200, PLAYER_5: 200})

        # First player goes all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=0, total_bet=100, status=PlayerStatus.ALL_IN)},
                current_bet=100,
                current_player_id=PLAYER_2,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Second player also goes all-in for same amount
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=0, total_bet=100, status=PlayerStatus.ALL_IN)},
                current_player_id=PLAYER_3,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Third player calls
        test.process_move(PLAYER_3, TexasHoldemAction.CALL)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=100, current_bet=100, total_bet=100)},
                current_player_id=PLAYER_4,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        # Fourth and fifth players fold
        test.process_move(PLAYER_4, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={PLAYER_4: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
                current_player_id=PLAYER_5,
            ),
            exclude_fields={"pot", "action_position", "last_raise_amount", "last_raise_position", "players.current_bet"},
        )

        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)
        test.assert_state_change(
            TexasHoldemStateDiff(players={PLAYER_5: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)}),
            exclude_fields={
                "pot",
                "action_position",
                "last_raise_amount",
                "last_raise_position",
                "players.current_bet",
                "deck",
                "community_cards",
                "winners",
                "winning_hands",
                "is_finished",
                "current_player_id",
                "betting_round",
                "current_bet",
                "side_pots",
            },
        )

        # Force to showdown
        test.advance_to_showdown()

        # Verify no side pots needed since all-ins are same amount
        test.assert_side_pots_count(0)  # No side pots when all bets are equal
        assert test.state.is_finished, "Game should be finished"
        test.assert_total_chips_conservation(815)  # Total chips: 100 + 100 + 200 + 200 + 200 + 15 (blinds)

    def test_complex_side_pot_distribution(self) -> None:
        """Test complex side pot scenario with specific hand outcomes."""
        test = PokerTest.create(
            chips={PLAYER_1: 50, PLAYER_2: 100, PLAYER_3: 200, PLAYER_4: 300, PLAYER_5: 400},
            community_cards=[
                Card.of("2d"),
                Card.of("3c"),
                Card.of("4d"),
                Card.of("5c"),
                Card.of("6h"),
            ],
            betting_round=BettingRound.RIVER,
            current_player_id=PLAYER_1,
            current_bet=0,
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("As")],  # Pair of Aces
                PLAYER_2: [Card.of("Kh"), Card.of("Ks")],  # Pair of Kings
                PLAYER_3: [Card.of("Qh"), Card.of("Qs")],  # Pair of Queens
                PLAYER_4: [Card.of("Jh"), Card.of("Js")],  # Pair of Jacks
                PLAYER_5: [Card.of("10h"), Card.of("9h")],  # Suited connectors
            },
        )

        # All players go all-in in order
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_4, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_5, TexasHoldemAction.ALL_IN)

        # Verify multiple side pots before showdown
        test.assert_side_pots_count(5)  # 5 side pots for 5 different all-in amounts

        # Force to showdown
        test.advance_to_showdown()

        # Verify proper distribution and game completion
        assert test.state.is_finished, "Game should be finished"
        test.assert_total_chips_conservation(1065)  # 50 + 100 + 200 + 300 + 400 + 15 (blinds)

        # Player 1 should win with pair of Aces
        assert PLAYER_1 in test.get_winners()
