"""Extended tests for betting round edge cases in Texas Hold'em."""

from texas_holdem import BettingRound, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PLAYER_5, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestBettingRoundsExtended:
    """Test edge cases for betting round progression."""

    def test_betting_round_transition_with_exact_chips(self) -> None:
        """Test round transitions when players have exact chip amounts."""

        test = PokerTest.create(num_players=3, chips={PLAYER_1: 30, PLAYER_2: 25, PLAYER_3: 30})

        # Complete preflop with calls - UTG (player_1) calls first

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3,
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=20, current_bet=10, total_bet=10)},
                pot=30,
                action_position=2,
            )
        )

        # Big blind (player_3) should have the option to check since everyone just called

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        test.assert_state_change(
            TexasHoldemStateDiff(
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
            exclude_fields={"community_cards", "deck"},
        )

    def test_action_position_with_folded_players(self) -> None:
        """Test action position calculation when players fold in different positions."""

        test = PokerTest.create(num_players=4)

        # Player 1 (UTG) folds

        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_2,
                action_position=1,
                players={PLAYER_1: TexasHoldemPlayerDiff(status=PlayerStatus.FOLDED)},
            )
        )

        # Player 2 calls

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3,
                action_position=2,
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=25,
            )
        )

        # Player 3 (small blind) calls to match the big blind

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_4,
                action_position=3,
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=990, current_bet=10, total_bet=10)},
                pot=30,
            )
        )

    def test_betting_amount_reset_between_rounds(self) -> None:
        """Test that betting amounts properly reset between rounds."""

        test = PokerTest.create()

        # Preflop: Player 1 raises significantly

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=100)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_2,
                players={PLAYER_1: TexasHoldemPlayerDiff(chips=900, current_bet=100, total_bet=100)},
                pot=115,
                current_bet=100,
                action_position=1,
                last_raise_amount=100,
                last_raise_position=0,
            )
        )

        # Others call

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_3,
                action_position=2,
                players={PLAYER_2: TexasHoldemPlayerDiff(chips=900, current_bet=100, total_bet=100)},
                pot=215,
            )
        )

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                current_player_id=PLAYER_4,
                action_position=3,
                players={PLAYER_3: TexasHoldemPlayerDiff(chips=900, current_bet=100, total_bet=100)},
                pot=315,
            )
        )

        # Complete the betting round

        test.process_move(PLAYER_4, TexasHoldemAction.CALL)

        test.process_move(PLAYER_5, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_bet=0,
                current_player_id=PLAYER_2,  # Small blind acts first on flop
                action_position=1,
                last_raise_amount=0,
                players={PLAYER_5: TexasHoldemPlayerDiff(chips=900, total_bet=100)},
                pot=500,
            ),
            exclude_fields={"community_cards", "deck", "players.current_bet"},
        )

        # Players should be able to check

        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

    def test_community_card_dealing_validation(self) -> None:
        """Test proper community card dealing between rounds."""

        test = PokerTest.create()

        # Initially no community cards

        assert len(test.get_community_cards()) == 0

        # Complete preflop

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.process_move(PLAYER_4, TexasHoldemAction.CALL)  # Small blind calls

        test.process_move(PLAYER_5, TexasHoldemAction.CHECK)  # Big blind can check

        test.assert_state_change(
            TexasHoldemStateDiff(betting_round=BettingRound.FLOP, current_player_id=PLAYER_2),
            exclude_fields={"community_cards", "deck", "players.current_bet", "current_bet", "action_position"},
        )

        assert len(test.get_community_cards()) == 3  # Should have 3 flop cards

        # Complete flop

        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)  # Small blind acts first

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)  # Big blind

        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)  # Next in position

        test.process_move(PLAYER_5, TexasHoldemAction.CHECK)

        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)  # UTG

        test.assert_state_change(
            TexasHoldemStateDiff(betting_round=BettingRound.TURN, current_player_id=PLAYER_2),
            exclude_fields={"community_cards", "deck", "players.current_bet", "current_bet", "action_position"},
        )

        assert len(test.get_community_cards()) == 4  # Should have 4 cards (flop + turn)

        # Complete turn

        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)  # Small blind acts first

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)  # Big blind

        test.process_move(PLAYER_4, TexasHoldemAction.CHECK)  # Next in position

        test.process_move(PLAYER_5, TexasHoldemAction.CHECK)

        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)  # UTG

        test.assert_state_change(
            TexasHoldemStateDiff(betting_round=BettingRound.RIVER, current_player_id=PLAYER_2),
            exclude_fields={"community_cards", "deck", "players.current_bet", "current_bet", "action_position"},
        )

        assert len(test.get_community_cards()) == 5  # Should have 5 cards (flop + turn + river)

    def test_round_progression_with_mixed_statuses(self) -> None:
        """Test round progression with combination of active/folded/all-in players."""

        test = PokerTest.create(chips={PLAYER_1: 50, PLAYER_2: 200, PLAYER_3: 200, PLAYER_4: 200, PLAYER_5: 200})

        # Player 1 (UTG) goes all-in

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        # Player 2 folds

        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)

        # Player 3 calls

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # Player 4 calls

        test.process_move(PLAYER_4, TexasHoldemAction.CALL)

        # Player 5 calls

        test.process_move(PLAYER_5, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_player_id=PLAYER_3,  # Small blind (Player 3) acts first on flop
            ),
            exclude_fields={"action_position", "current_bet", "last_raise_amount", "pot", "community_cards", "deck", "players"},
        )

    def test_heads_up_position_handling(self) -> None:
        """Test position changes in heads-up scenarios."""

        test = PokerTest.create(num_players=2)

        # In heads-up, small blind is dealer and acts first preflop

        assert test.state.dealer_position == 0

        assert test.state.small_blind_position == 0

        assert test.state.big_blind_position == 1
        assert test.state.current_player_id == PLAYER_1  # Small blind acts first preflop

        # Complete preflop

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
            ),
            exclude_fields={"current_bet", "players", "community_cards", "deck", "action_position", "last_raise_amount", "pot", "current_player_id"},
        )

    def test_betting_round_with_all_players_all_in(self) -> None:
        """Test round progression when all players are all-in."""

        test = PokerTest.create(chips={PLAYER_1: 50, PLAYER_2: 50, PLAYER_3: 50, PLAYER_4: 50, PLAYER_5: 50})

        # All players go all-in

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)

        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)

        test.process_move(PLAYER_4, TexasHoldemAction.ALL_IN)

        test.process_move(PLAYER_5, TexasHoldemAction.ALL_IN)

        test.assert_state_change(
            TexasHoldemStateDiff(betting_round=BettingRound.SHOWDOWN, is_finished=True),
            exclude_fields={
                "current_bet",
                "last_raise_amount",
                "players",
                "pot",
                "side_pots",
                "winners",
                "winning_hands",
                "community_cards",
                "deck",
                "action_position",
                "current_player_id",
            },
        )

    def test_action_position_edge_cases(self) -> None:
        """Test action position calculation in edge cases."""

        test = PokerTest.create(num_players=3)

        # Complete preflop to get to flop

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_player_id=PLAYER_2,  # On flop, small blind should act first
            ),
            exclude_fields={"current_bet", "players", "action_position", "last_raise_amount", "pot", "community_cards", "deck"},
        )

        # Small blind folds

        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)

        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_3), exclude_fields={"betting_round", "action_position", "players", "deck", "community_cards"}
        )

        # Big blind checks

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        test.assert_state_change(
            TexasHoldemStateDiff(current_player_id=PLAYER_1), exclude_fields={"betting_round", "action_position", "players", "deck", "community_cards"}
        )

    def test_betting_round_completion_validation(self) -> None:
        """Test validation that betting rounds complete properly."""

        test = PokerTest.create(num_players=3)

        # Player 1 raises

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=50)

        # Player 2 calls

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        assert test.get_betting_round() == BettingRound.PREFLOP  # Before player 3 acts, round should not be complete

        # Player 3 calls

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(betting_round=BettingRound.FLOP),  # Now round should be complete and advance to flop
            exclude_fields={"current_player_id", "players", "pot", "action_position", "current_bet", "last_raise_amount", "community_cards", "deck"},
        )

    def test_side_pot_creation_during_round_transition(self) -> None:
        """Test side pot creation when transitioning between rounds."""

        test = PokerTest.create(num_players=3, chips={PLAYER_1: 30, PLAYER_2: 100, PLAYER_3: 100})

        # Player 1 goes all-in

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)

        # Player 2 calls

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        # Player 3 calls

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.assert_state_change(
            TexasHoldemStateDiff(
                betting_round=BettingRound.FLOP,
                current_player_id=PLAYER_2,  # Only players 2 and 3 should be able to act on flop
            ),
            exclude_fields={"pot", "current_bet", "action_position", "last_raise_amount", "community_cards", "deck", "players"},
        )

    def test_betting_round_with_single_active_player(self) -> None:
        """Test round progression when only one player remains active."""

        test = PokerTest.create()

        # Player 1 raises big

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=200)

        # Player 2 folds

        test.process_move(PLAYER_2, TexasHoldemAction.FOLD)

        # Player 3 folds

        test.process_move(PLAYER_3, TexasHoldemAction.FOLD)

        # Player 4 folds

        test.process_move(PLAYER_4, TexasHoldemAction.FOLD)

        # Player 5 folds

        test.process_move(PLAYER_5, TexasHoldemAction.FOLD)

        test.assert_state_change(
            TexasHoldemStateDiff(is_finished=True, winners=[PLAYER_1]),
            exclude_fields={"current_player_id", "players", "current_bet", "betting_round", "action_position", "last_raise_amount", "winning_hands", "deck"},
        )

    def test_big_blind_check_when_betting_round_stabilizes(self) -> None:
        """Test that big blind can check when betting round has stabilized on an amount."""

        test = PokerTest.create()

        # Player 1 (UTG) raises to 30

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=30)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=30))

        # Player 2 (small blind) calls the 30

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=30))

        # Big blind calls to match the 30 bet

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP, current_bet=0, current_player_id=PLAYER_2))

        # Small blind checks

        test.process_move(PLAYER_2, TexasHoldemAction.CHECK)

        # Big blind checks

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        # UTG checks - this should complete the flop betting round

        test.process_move(PLAYER_1, TexasHoldemAction.CHECK)

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.TURN))

    def test_big_blind_check_option_after_limpers(self) -> None:
        """Test big blind check option when all players just call (limp)."""

        test = PokerTest.create()

        # Player 1 (UTG) calls (limps)

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=10))

        # Player 2 (small blind) calls

        test.process_move(PLAYER_2, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=10))

        # Big blind checks (no additional bet needed)

        test.process_move(PLAYER_3, TexasHoldemAction.CHECK)

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP, current_bet=0, current_player_id=PLAYER_2))

    def test_betting_round_stabilization_with_raises(self) -> None:
        """Test betting round stabilization after multiple raises."""

        test = PokerTest.create()

        # Player 1 raises to 25

        test.process_move(PLAYER_1, TexasHoldemAction.RAISE, amount=25)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=25))

        # Player 2 re-raises to 50

        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=50)

        test.assert_state_change(TexasHoldemStateDiff(current_bet=50))

        # Player 3 (big blind) calls the 50

        test.process_move(PLAYER_3, TexasHoldemAction.CALL)

        # Back to Player 1 who needs to call the additional 25 (50 - 25)

        test.process_move(PLAYER_1, TexasHoldemAction.CALL)

        test.assert_state_change(TexasHoldemStateDiff(betting_round=BettingRound.FLOP, current_bet=0, current_player_id=PLAYER_2))
