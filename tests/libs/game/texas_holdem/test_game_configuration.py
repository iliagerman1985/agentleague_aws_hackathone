"""Tests for game configuration in Texas Hold'em."""

from texas_holdem import BettingRound, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest


class TestGameConfiguration:
    """Test game configuration and settings."""

    def test_default_configuration(self) -> None:
        """Test default game configuration values."""
        test = PokerTest.create(num_players=4)

        # Verify default blind structure
        assert test.config.small_blind == 5
        assert test.config.big_blind == 10

        # Verify default starting chips
        for player in test.state.players:
            # Each player should have starting chips minus any blinds posted
            if player.player_id in {PLAYER_2, PLAYER_3}:  # Small blind
                assert player.chips + player.total_bet == 1000
            else:
                assert player.chips == 1000

    def test_custom_blind_structure(self) -> None:
        """Test custom blind amounts."""
        test = PokerTest.create(num_players=3)

        # Create game with custom blinds
        test = PokerTest.create(num_players=4, small_blind=25, big_blind=50)

        # Verify custom blind amounts
        assert test.config.small_blind == 25
        assert test.config.big_blind == 50

        # Verify blinds are posted correctly
        small_blind_player = test.state.players[test.state.small_blind_position]
        big_blind_player = test.state.players[test.state.big_blind_position]

        assert small_blind_player.total_bet == 25
        assert big_blind_player.total_bet == 50

    def test_custom_starting_chips(self) -> None:
        """Test custom starting chip amounts."""
        test = PokerTest.create(num_players=4, starting_chips=500)

        # Verify starting chips (minus blinds)
        for player in test.state.players:
            if player.player_id in {PLAYER_2, PLAYER_3}:  # Small blind
                assert player.chips + player.total_bet == 500
            else:
                assert player.chips == 500

    def test_minimum_players_configuration(self) -> None:
        """Test configuration with minimum number of players."""
        test = PokerTest.create(num_players=2)

        # Verify heads-up setup
        assert len(test.state.players) == 2
        assert test.state.dealer_position == 0
        assert test.state.small_blind_position == 0  # Dealer is small blind in heads-up
        assert test.state.big_blind_position == 1

    def test_maximum_players_configuration(self) -> None:
        """Test configuration with maximum number of players."""
        test = PokerTest.create(num_players=5)

        # Verify full table setup
        assert len(test.state.players) == 5
        assert test.state.dealer_position == 0
        assert test.state.small_blind_position == 1
        assert test.state.big_blind_position == 2
        assert test.state.action_position == 3  # UTG

    def test_blind_ratio_validation(self) -> None:
        """Test validation of blind ratios."""
        test = PokerTest.create(num_players=3)

        # Test standard 2:1 ratio
        test = PokerTest.create(num_players=4, small_blind=10, big_blind=20)

        assert test.config.big_blind == 2 * test.config.small_blind

        # Test non-standard but valid ratio
        test = PokerTest.create(num_players=4, small_blind=15, big_blind=30)

        assert test.config.big_blind == 2 * test.config.small_blind

    def test_insufficient_chips_for_blinds(self) -> None:
        """Test configuration where starting chips are insufficient for blinds."""
        test = PokerTest.create(
            num_players=4,
            starting_chips=15,  # Less than big blind
            small_blind=5,
            big_blind=20,
        )

        # Players should be able to post partial blinds and go all-in
        small_blind_player = test.state.players[test.state.small_blind_position]
        big_blind_player = test.state.players[test.state.big_blind_position]

        # Small blind should post full amount (5)
        assert small_blind_player.total_bet == 5
        assert small_blind_player.chips == 10

        # Big blind should post all remaining chips (15)
        assert big_blind_player.total_bet == 15
        assert big_blind_player.chips == 0
        assert big_blind_player.status == PlayerStatus.ALL_IN

    def test_equal_chips_and_big_blind(self) -> None:
        """Test configuration where starting chips equal big blind."""
        test = PokerTest.create(num_players=4, starting_chips=20, small_blind=5, big_blind=20)

        # Big blind player should be all-in
        big_blind_player = test.state.players[test.state.big_blind_position]
        assert big_blind_player.total_bet == 20
        assert big_blind_player.chips == 0
        assert big_blind_player.status == PlayerStatus.ALL_IN

    def test_fractional_blind_amounts(self) -> None:
        """Test handling of fractional blind amounts (should be integers)."""
        test = PokerTest.create(num_players=3)

        # Ensure blinds are always integers
        test = PokerTest.create(num_players=4, small_blind=2, big_blind=5)

        assert isinstance(test.config.small_blind, int)
        assert isinstance(test.config.big_blind, int)
        assert test.config.small_blind == 2
        assert test.config.big_blind == 5

    def test_minimal_blind_configuration(self) -> None:
        """Test configuration with minimal blinds (near-freeroll scenario)."""
        test = PokerTest.create(num_players=4, small_blind=1, big_blind=2)

        # Minimal blinds should be posted
        small_blind_player = test.state.players[test.state.small_blind_position]
        big_blind_player = test.state.players[test.state.big_blind_position]
        assert small_blind_player.total_bet == 1
        assert big_blind_player.total_bet == 2

        # Other players should have no bets
        for player in test.state.players:
            if player not in (small_blind_player, big_blind_player):
                assert player.total_bet == 0

    def test_large_blind_configuration(self) -> None:
        """Test configuration with very large blinds."""
        test = PokerTest.create(num_players=4, starting_chips=10000, small_blind=1000, big_blind=2000)

        # Verify large blinds are posted correctly
        small_blind_player = test.state.players[test.state.small_blind_position]
        big_blind_player = test.state.players[test.state.big_blind_position]

        assert small_blind_player.total_bet == 1000
        assert big_blind_player.total_bet == 2000

        # Players should still have chips remaining
        assert small_blind_player.chips == 9000
        assert big_blind_player.chips == 8000

    def test_player_id_configuration(self) -> None:
        """Test configuration with different player ID formats."""
        test = PokerTest.create(num_players=4)

        # Verify player IDs are set correctly
        expected_ids = [PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4]
        actual_ids = [player.player_id for player in test.state.players]

        assert actual_ids == expected_ids

    def test_position_configuration_consistency(self) -> None:
        """Test that position configuration is consistent."""
        test = PokerTest.create(num_players=3)

        for num_players in range(2, 6):  # Test 2-5 players
            test = PokerTest.create(num_players=num_players)

            # Verify position constraints
            assert 0 <= test.state.dealer_position < num_players
            assert 0 <= test.state.small_blind_position < num_players
            assert 0 <= test.state.big_blind_position < num_players
            assert 0 <= test.state.action_position < num_players

            # Verify position relationships
            if num_players == 2:
                # Heads-up: dealer is small blind
                assert test.state.dealer_position == test.state.small_blind_position
                assert test.state.big_blind_position == (test.state.dealer_position + 1) % num_players
            else:
                # Multi-way: dealer, small blind, big blind in order
                assert test.state.small_blind_position == (test.state.dealer_position + 1) % num_players
                assert test.state.big_blind_position == (test.state.dealer_position + 2) % num_players

    def test_game_state_initialization(self) -> None:
        """Test proper game state initialization."""
        test = PokerTest.create()

        # Verify initial game state
        assert test.state.betting_round == BettingRound.PREFLOP
        assert len(test.state.community_cards) == 0
        assert len(test.state.deck) == 52 - (4 * 2)  # 52 cards minus hole cards

        # Verify initial pot (blinds are immediately added to pot)
        expected_pot = 5 + 10  # Default small_blind + big_blind
        assert test.state.pot == expected_pot

        # Verify all players have hole cards
        for player in test.state.players:
            assert len(player.hole_cards) == 2

    def test_deck_configuration(self) -> None:
        """Test deck configuration and initialization."""
        test = PokerTest.create(num_players=4)

        # Verify deck is properly initialized
        total_cards = len(test.state.deck)
        hole_cards = sum(len(player.hole_cards) for player in test.state.players)
        community_cards = len(test.state.community_cards)

        assert total_cards + hole_cards + community_cards == 52

        # Verify no duplicate cards
        all_cards = list(test.state.deck)
        for player in test.state.players:
            all_cards.extend(player.hole_cards)
        all_cards.extend(test.state.community_cards)

        # Convert cards to strings for comparison
        card_strings = [f"{card.rank}_{card.suit}" for card in all_cards]
        assert len(card_strings) == len(set(card_strings))  # No duplicates

    def test_betting_structure_configuration(self) -> None:
        """Test betting structure configuration."""
        test = PokerTest.create(num_players=4)

        # Test minimum bet is big blind
        # Find the current player who should act (action_position)
        current_player = test.state.get_player_by_position(test.state.action_position)
        assert current_player is not None

        # Try to bet less than big blind (should fail or auto-adjust)
        error = test.process_move_error(current_player.player_id, TexasHoldemAction.RAISE, amount=5)
        assert error is not None
        assert error and "minimum" in error.details.message.lower()

    def test_side_pot_configuration(self) -> None:
        """Test side pot configuration in all-in scenarios."""
        test = PokerTest.create(num_players=4)

        # Create all-in scenario with limited chips
        test = PokerTest.create(num_players=4, chips={PLAYER_1: 20})

        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.RAISE, amount=50)

        # Verify side pot structure is initialized
        assert hasattr(test.state, "side_pots")
        assert isinstance(test.state.side_pots, list)

    def test_tournament_style_configuration(self) -> None:
        """Test configuration suitable for tournament play."""
        test = PokerTest.create(num_players=5, starting_chips=1500, small_blind=25, big_blind=50)

        # Verify tournament-style setup
        assert len(test.state.players) == 5
        assert test.config.small_blind == 25
        assert test.config.big_blind == 50

        # Verify all players have equal starting stacks
        for player in test.state.players:
            total_chips = player.chips + player.total_bet
            assert total_chips == 1500

    def test_cash_game_configuration(self) -> None:
        """Test configuration suitable for cash game play."""
        test = PokerTest.create(num_players=5, starting_chips=10000, small_blind=50, big_blind=100)

        # Verify cash game setup
        assert len(test.state.players) == 5
        assert test.config.small_blind == 50
        assert test.config.big_blind == 100

        # Verify deep stack setup (100+ big blinds)
        for player in test.state.players:
            total_chips = player.chips + player.total_bet
            assert total_chips >= 100 * test.config.big_blind
