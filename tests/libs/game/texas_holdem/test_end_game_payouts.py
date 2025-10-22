"""Tests for end-of-game payouts and chip distribution in Texas Hold'em."""

import pytest
from texas_holdem import Card, CardRank, CardSuit, PlayerStatus, TexasHoldemAction

from .test_helpers import PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PokerTest, TexasHoldemPlayerDiff, TexasHoldemStateDiff


class TestEndGamePayouts:
    """Test exact chip amounts each player receives at game end."""

    def test_simple_winner_takes_all(self) -> None:
        """Test simple scenario where one player wins entire pot."""
        # Set up game with specific chip amounts and deterministic outcome
        test = PokerTest.create(
            num_players=3,
            chips={PLAYER_1: 100, PLAYER_2: 100, PLAYER_3: 100},
            hole_cards={
                PLAYER_1: [Card(rank=CardRank.ACE, suit=CardSuit.HEARTS), Card(rank=CardRank.ACE, suit=CardSuit.SPADES)],
                PLAYER_2: [Card(rank=CardRank.KING, suit=CardSuit.HEARTS), Card(rank=CardRank.QUEEN, suit=CardSuit.HEARTS)],
                PLAYER_3: [Card(rank=CardRank.TWO, suit=CardSuit.CLUBS), Card(rank=CardRank.THREE, suit=CardSuit.CLUBS)],
            },
        )

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)

        # Force game to completion
        test.advance_to_showdown()

        # Verify final chip distribution
        # PLAYER_1 should win everything (trips aces beats all)
        # Total pot: 100 + 100 + 100 = 300
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(chips=300, status=PlayerStatus.ACTIVE),
                    PLAYER_2: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN),
                    PLAYER_3: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN),
                },
                is_finished=True,
                winners=[PLAYER_1],
            )
        )

    def test_two_way_side_pot_distribution(self) -> None:
        """Test exact chip distribution with two-way side pot."""
        # Set up unequal stacks to create side pot
        test = PokerTest.create(
            num_players=3,
            chips={PLAYER_1: 50, PLAYER_2: 100, PLAYER_3: 100},
            hole_cards={
                PLAYER_1: [Card(rank=CardRank.ACE, suit=CardSuit.HEARTS), Card(rank=CardRank.ACE, suit=CardSuit.SPADES)],
                PLAYER_2: [Card(rank=CardRank.KING, suit=CardSuit.HEARTS), Card(rank=CardRank.KING, suit=CardSuit.SPADES)],
                PLAYER_3: [Card(rank=CardRank.QUEEN, suit=CardSuit.HEARTS), Card(rank=CardRank.QUEEN, suit=CardSuit.SPADES)],
            },
        )

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)  # 50 chips
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)  # 100 chips
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)  # 100 chips

        # Force game to completion
        test.advance_to_showdown()

        # Verify exact chip distribution:
        # Main pot: 50 * 3 = 150 (PLAYER_1 wins with aces)
        # Side pot: (100-50) * 2 = 100 (PLAYER_2 wins with kings over queens)
        # Final: PLAYER_1 = 150, PLAYER_2 = 100, PLAYER_3 = 0
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(chips=150, status=PlayerStatus.ALL_IN),
                    PLAYER_2: TexasHoldemPlayerDiff(chips=100, status=PlayerStatus.ALL_IN),
                    PLAYER_3: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN),
                },
                is_finished=True,
                winners=[PLAYER_1, PLAYER_2],  # Both win their respective pots
            )
        )

    def test_three_way_complex_side_pots(self) -> None:
        """Test complex three-way side pot distribution."""
        # Set up three different stack sizes
        test = PokerTest.create(
            num_players=4,
            chips={PLAYER_1: 30, PLAYER_2: 60, PLAYER_3: 90, PLAYER_4: 120},
            hole_cards={
                PLAYER_1: [Card(rank=CardRank.ACE, suit=CardSuit.HEARTS), Card(rank=CardRank.ACE, suit=CardSuit.SPADES)],
                PLAYER_2: [Card(rank=CardRank.KING, suit=CardSuit.HEARTS), Card(rank=CardRank.KING, suit=CardSuit.SPADES)],
                PLAYER_3: [Card(rank=CardRank.QUEEN, suit=CardSuit.HEARTS), Card(rank=CardRank.QUEEN, suit=CardSuit.SPADES)],
                PLAYER_4: [Card(rank=CardRank.JACK, suit=CardSuit.HEARTS), Card(rank=CardRank.JACK, suit=CardSuit.SPADES)],
            },
        )

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)  # 30 chips
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)  # 60 chips
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)  # 90 chips
        test.process_move(PLAYER_4, TexasHoldemAction.ALL_IN)  # 120 chips

        # Force game to completion
        test.advance_to_showdown()

        # Verify exact chip distribution:
        # Main pot (30*4=120): PLAYER_1 wins with aces
        # Side pot 1 ((60-30)*3=90): PLAYER_2 wins with kings
        # Side pot 2 ((90-60)*2=60): PLAYER_3 wins with queens
        # Side pot 3 (120-90=30): PLAYER_4 gets back uncalled bet
        # Final: PLAYER_1=120, PLAYER_2=90, PLAYER_3=60, PLAYER_4=30
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(chips=120, status=PlayerStatus.ALL_IN),
                    PLAYER_2: TexasHoldemPlayerDiff(chips=90, status=PlayerStatus.ALL_IN),
                    PLAYER_3: TexasHoldemPlayerDiff(chips=60, status=PlayerStatus.ALL_IN),
                    PLAYER_4: TexasHoldemPlayerDiff(chips=30, status=PlayerStatus.ALL_IN),
                },
                is_finished=True,
                winners=[PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4],  # Each wins their respective pot
            )
        )

    def test_split_pot_equal_hands(self) -> None:
        """Test chip distribution when players have equal hands."""
        # Set up identical hands for split pot
        test = PokerTest.create(
            num_players=3,
            chips={PLAYER_1: 100, PLAYER_2: 100, PLAYER_3: 100},
            hole_cards={
                PLAYER_1: [Card(rank=CardRank.ACE, suit=CardSuit.HEARTS), Card(rank=CardRank.KING, suit=CardSuit.HEARTS)],
                PLAYER_2: [Card(rank=CardRank.ACE, suit=CardSuit.SPADES), Card(rank=CardRank.KING, suit=CardSuit.SPADES)],
                PLAYER_3: [Card(rank=CardRank.TWO, suit=CardSuit.CLUBS), Card(rank=CardRank.THREE, suit=CardSuit.CLUBS)],
            },
        )

        # All players go all-in
        test.process_move(PLAYER_1, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_2, TexasHoldemAction.ALL_IN)
        test.process_move(PLAYER_3, TexasHoldemAction.ALL_IN)

        # Force game to completion
        test.advance_to_showdown()

        # Verify split pot distribution:
        # PLAYER_1 and PLAYER_2 both have royal straight, split 300 chips
        # Each gets 150 chips, PLAYER_3 gets 0
        test.assert_state_change(
            TexasHoldemStateDiff(
                players={
                    PLAYER_1: TexasHoldemPlayerDiff(chips=150, status=PlayerStatus.ALL_IN),
                    PLAYER_2: TexasHoldemPlayerDiff(chips=150, status=PlayerStatus.ALL_IN),
                    PLAYER_3: TexasHoldemPlayerDiff(chips=0, status=PlayerStatus.ALL_IN),
                },
                is_finished=True,
                winners=[PLAYER_1, PLAYER_2],  # Split pot winners
            )
        )

    def test_invalid_payout_validation(self) -> None:
        """Test validation of invalid payout scenarios."""
        test = PokerTest.create()

        # Test trying to set invalid chip amounts should be caught by game logic
        # This is more of a conceptual test - in practice, the game engine should prevent this
        test.state.players[0].chips = -100  # Negative chips

        # The game should detect this as invalid when trying to make moves
        with pytest.raises((ValueError, RuntimeError, AssertionError)):
            test.process_move(PLAYER_1, TexasHoldemAction.CALL)
