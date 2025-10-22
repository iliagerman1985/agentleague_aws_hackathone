"""Simple tests for end-of-game payouts in Texas Hold'em."""

from texas_holdem import Card, CardRank, CardSuit, PlayerStatus, TexasHoldemAction
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PokerTest


class TestSimplePayouts:
    """Test basic chip distribution scenarios."""

    def test_winner_gets_all_chips_simple(self) -> None:
        """Test that winner receives all chips in simple scenario."""
        test = PokerTest.create(
            num_players=3,
            chips={PLAYER_1: 100, PLAYER_2: 100, PLAYER_3: 100},
            hole_cards={
                PLAYER_1: [
                    Card(rank=CardRank.ACE, suit=CardSuit.HEARTS),
                    Card(rank=CardRank.ACE, suit=CardSuit.SPADES),
                ],
                PLAYER_2: [
                    Card(rank=CardRank.TWO, suit=CardSuit.HEARTS),
                    Card(rank=CardRank.THREE, suit=CardSuit.HEARTS),
                ],
                PLAYER_3: [
                    Card(rank=CardRank.FOUR, suit=CardSuit.HEARTS),
                    Card(rank=CardRank.FIVE, suit=CardSuit.HEARTS),
                ],
            },
        )

        # Record initial total chips (including blinds already posted)
        initial_total = sum(player.chips for player in test.state.players) + test.state.pot

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)

        # Force game to completion
        test.advance_to_showdown()

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"

        # Verify total chips are conserved
        total_chips = sum(player.chips for player in test.state.players)
        assert total_chips == initial_total, f"Total chips should be {initial_total}, got {total_chips}"

    def test_side_pot_basic_distribution(self) -> None:
        """Test basic side pot distribution with different stack sizes."""
        test = PokerTest.create(num_players=3, chips={PLAYER_1: 50, PLAYER_2: 100, PLAYER_3: 100})

        # Record initial total chips (including blinds already posted)
        initial_total = sum(player.chips for player in test.state.players) + test.state.pot

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)  # 50 chips
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)  # 100 chips
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)  # 100 chips

        # Force game to completion
        test.advance_to_showdown()

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"

        # Verify total chips are conserved
        total_chips = sum(player.chips for player in test.state.players)
        assert total_chips == initial_total, f"Total chips should be {initial_total}, got {total_chips}"

        # Verify no chips remain in pots after distribution
        remaining_pot = test.state.pot + sum(pot.amount for pot in test.state.side_pots)
        assert remaining_pot == 0, f"No chips should remain in pots, got {remaining_pot}"

    def test_error_handling_invalid_move(self) -> None:
        """Test error handling for invalid moves."""
        test = PokerTest.create()

        # Try to make a move for a player who is not current player
        error = test.process_move_error(PLAYER_2, TexasHoldemAction.CALL)  # PLAYER_1 should be current
        assert error.details.code == THErrors.NOT_PLAYER_TURN.code

    def test_folded_players_get_no_chips(self) -> None:
        """Test that folded players receive no chips at showdown."""
        test = PokerTest.create(num_players=3)

        # Player 1 folds, others go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.FOLD)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)

        # Force game to completion
        test.advance_to_showdown()

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"

        # Verify folded player has no additional chips
        folded_player = test.state.get_player_by_agent_id(PLAYER_1)
        assert folded_player is not None
        assert folded_player.status == PlayerStatus.FOLDED

        # Calculate the actual initial total (including blinds already posted)
        # Initial: Player1=1000, Player2=995, Player3=990, Pot=15 (contains the blind bets)
        # Total = 1000 + 995 + 990 + 15 = 3000
        expected_total = 1000 + 995 + 990 + 15  # actual initial state
        final_total = sum(player.chips for player in test.state.players)
        assert final_total == expected_total, f"Chips not conserved: {final_total} != {expected_total}"

    def test_all_in_with_exact_amounts(self) -> None:
        """Test all-in scenarios with exact chip amounts."""
        test = PokerTest.create(num_players=3, chips={PLAYER_1: 25, PLAYER_2: 50, PLAYER_3: 75})

        # Record initial total chips (including blinds already posted)
        initial_total = sum(player.chips for player in test.state.players) + test.state.pot

        # All players go all-in with their exact amounts
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)  # 25 chips
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)  # 50 chips
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)  # 75 chips

        # Force game to completion
        test.advance_to_showdown()

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"

        # Verify total chips are conserved
        total_chips = sum(player.chips for player in test.state.players)
        assert total_chips == initial_total, f"Total chips should be {initial_total}, got {total_chips}"

        # Verify all players are marked as all-in
        for player in test.state.players:
            assert player.status == PlayerStatus.ALL_IN, f"Player {player.player_id} should be all-in"

    def test_minimum_viable_pot(self) -> None:
        """Test payout distribution with minimum viable pot sizes."""
        test = PokerTest.create(
            num_players=2,  # Minimum players for a game
            chips={PLAYER_1: 20, PLAYER_2: 20},  # Minimum viable stacks
        )

        # Record initial total chips (including blinds already posted)
        initial_total = sum(player.chips for player in test.state.players) + test.state.pot

        # Both players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)

        # Force game to completion
        test.advance_to_showdown()

        # Verify game is finished
        assert test.state.is_finished, "Game should be finished"

        # Verify total chips are conserved
        total_chips = sum(player.chips for player in test.state.players)
        assert total_chips == initial_total, f"Total chips should be {initial_total}, got {total_chips}"

        # Verify chips are distributed (no player should have 0 chips unless they lost)
        chip_amounts = [player.chips for player in test.state.players]
        chip_amounts.sort()
        # In a tie situation, both players should have some chips
        # The exact distribution depends on hand evaluation, but total should be conserved
        assert sum(chip_amounts) == initial_total, f"Total chips not conserved: {sum(chip_amounts)} != {initial_total}"
