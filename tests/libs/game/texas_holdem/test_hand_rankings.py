"""Tests for poker hand rankings and comparisons."""

from texas_holdem import BettingRound, Card, HandRank, HandResult, TexasHoldemAction, TexasHoldemState

from common.ids import AgentId

from .test_helpers import PLAYER_1, PLAYER_2, PokerTest


def _test_rank(hole_cards: dict[AgentId, list[Card]], community_cards: list[Card], winners: list[AgentId], winning_hands: dict[AgentId, HandResult]) -> None:
    """Helper function to test hand rankings at showdown."""

    test = PokerTest.create(
        num_players=len(hole_cards),
        betting_round=BettingRound.RIVER,
        current_bets={PLAYER_1: 0, PLAYER_2: 0},
        total_bets={PLAYER_1: 20, PLAYER_2: 20},
        pot=40,
        current_bet=0,
        hole_cards=hole_cards,
        community_cards=community_cards,
    )

    # All players check to showdown
    # Make sure we process moves in the correct turn order
    players_to_act = list(hole_cards.keys())
    current_player = test.state.current_player_id

    # Reorder players starting with current player
    if current_player in players_to_act:
        current_index = players_to_act.index(current_player)
        players_to_act = players_to_act[current_index:] + players_to_act[:current_index]

    for player_id in players_to_act:
        test.process_move(player_id, TexasHoldemAction.CHECK)

    expected_state = TexasHoldemState(
        **{k: v for k, v in test.state.model_dump().items() if k not in ["winners", "winning_hands"]},
        winners=winners,
        winning_hands=winning_hands,
    )

    test.assert_state(
        expected_state,
        exclude_fields={
            "players",
            "pot",
            "side_pots",
            "deck",
            "current_bet",
            "betting_round",
            "community_cards",
            "action_position",
            "current_player_id",
            "is_finished",
        },
    )


class TestHandRankings:
    """Test poker hand ranking and evaluation."""

    def test_royal_flush_detection(self) -> None:
        """Test royal flush hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kh")],
                PLAYER_2: [Card.of("2c"), Card.of("3c")],
            },
            community_cards=[
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("10h"),
                Card.of("4d"),
                Card.of("7s"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
                PLAYER_2: HandResult(rank=HandRank.HIGH_CARD, high_cards=[12, 11], description="High Card"),
            },
        )

    def test_straight_flush_detection(self) -> None:
        """Test straight flush hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("9s"), Card.of("8s")],
                PLAYER_2: [Card.of("2c"), Card.of("3c")],
            },
            community_cards=[
                Card.of("7s"),
                Card.of("6s"),
                Card.of("5s"),
                Card.of("Kh"),
                Card.of("Ad"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[9], description="Straight Flush"),
                PLAYER_2: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13], description="High Card"),
            },
        )

    def test_four_of_a_kind_detection(self) -> None:
        """Test four of a kind hand ranking."""
        _test_rank(
            hole_cards={PLAYER_1: [Card.of("Ah"), Card.of("Ad")], PLAYER_2: [Card.of("2c"), Card.of("3c")]},
            community_cards=[Card.of("Ac"), Card.of("As"), Card.of("7h"), Card.of("Kd"), Card.of("Qs")],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[14, 13], description="Four of a Kind")},
        )

    def test_full_house_detection(self) -> None:
        """Test full house hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Kd")],
                PLAYER_2: [Card.of("2c"), Card.of("3c")],
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("7h"),
                Card.of("7s"),
                Card.of("Ad"),
                Card.of("Qs"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[13, 7], description="Full House")},
        )

    def test_flush_detection(self) -> None:
        """Test flush hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ad"), Card.of("10d")],
                PLAYER_2: [Card.of("2c"), Card.of("3c")],
            },
            community_cards=[
                Card.of("8d"),
                Card.of("6d"),
                Card.of("4d"),
                Card.of("7h"),
                Card.of("Ks"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush")},
        )

    def test_straight_detection(self) -> None:
        """Test straight hand ranking (wheel)."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("2s")],
                PLAYER_2: [Card.of("Kc"), Card.of("Qd")],
            },
            community_cards=[
                Card.of("3d"),
                Card.of("4c"),
                Card.of("5h"),
                Card.of("7s"),
                Card.of("9c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[5], description="Straight")},
        )

    def test_straight_ace_high(self) -> None:
        """Test ace-high straight."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Ks")],
                PLAYER_2: [Card.of("8c"), Card.of("7d")],
            },
            community_cards=[
                Card.of("Qd"),
                Card.of("Jc"),
                Card.of("9h"),  # Almost straight: A-K-Q-J-9 (missing 10)
                Card.of("4s"),
                Card.of("2c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[14], description="Straight")},
        )

    def test_three_of_a_kind_detection(self) -> None:
        """Test three of a kind hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Qh"), Card.of("Qd")],
                PLAYER_2: [Card.of("2c"), Card.of("3c")],
            },
            community_cards=[
                Card.of("Qc"),
                Card.of("7h"),
                Card.of("5s"),
                Card.of("Ad"),
                Card.of("Ks"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[12, 14], description="Three of a Kind")},
        )

    def test_two_pair_detection(self) -> None:
        """Test two pair hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Qd")],
                PLAYER_2: [Card.of("2c"), Card.of("3c")],
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("Qh"),
                Card.of("7s"),
                Card.of("5d"),
                Card.of("4s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.TWO_PAIR, high_cards=[13, 12], description="Two Pair")},
        )

    def test_pair_detection(self) -> None:
        """Test pair hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("As")],
                PLAYER_2: [Card.of("Kc"), Card.of("Qd")],
            },
            community_cards=[
                Card.of("Kh"),
                Card.of("Qs"),
                Card.of("7c"),
                Card.of("5h"),
                Card.of("3d"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.PAIR, high_cards=[14, 9], description="Pair")},
        )

    def test_high_card_detection(self) -> None:
        """Test high card hand ranking."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kd")],
                PLAYER_2: [Card.of("Qc"), Card.of("Js")],
            },
            community_cards=[
                Card.of("9c"),
                Card.of("7h"),
                Card.of("5s"),
                Card.of("3d"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13], description="High Card")},
        )

    def test_hand_comparison_royal_vs_straight_flush(self) -> None:
        """Test that royal flush beats straight flush."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kh")],
                PLAYER_2: [Card.of("9s"), Card.of("8s")],
            },
            community_cards=[
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("10h"),
                Card.of("7s"),
                Card.of("6s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush")},
        )

    def test_flush_comparison_by_high_card(self) -> None:
        """Test flush comparison by high card."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("9h")],
                PLAYER_2: [Card.of("Ks"), Card.of("Qs")],
            },
            community_cards=[
                Card.of("7h"),
                Card.of("5h"),
                Card.of("3h"),
                Card.of("Js"),
                Card.of("10s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush")},
        )

    def test_pair_comparison_by_kicker(self) -> None:
        """Test pair comparison by kicker."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kd")],
                PLAYER_2: [Card.of("Ac"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("As"),
                Card.of("7c"),
                Card.of("5h"),
                Card.of("3d"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.PAIR, high_cards=[14, 13], description="Pair")},
        )

    def test_straight_comparison_identical_high_card(self) -> None:
        """Test straight comparison with identical high cards (tie)."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("10h"), Card.of("9s")],
                PLAYER_2: [Card.of("10c"), Card.of("9d")],
            },
            community_cards=[
                Card.of("8d"),
                Card.of("7c"),
                Card.of("6h"),
                Card.of("As"),
                Card.of("Kc"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[10], description="Straight"),
                PLAYER_2: HandResult(rank=HandRank.STRAIGHT, high_cards=[10], description="Straight"),
            },
        )

    def test_wheel_vs_higher_straight(self) -> None:
        """Test wheel (A-2-3-4-5) vs higher straight."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("2s")],
                PLAYER_2: [Card.of("6c"), Card.of("7d")],
            },
            community_cards=[
                Card.of("3d"),
                Card.of("4c"),
                Card.of("5h"),
                Card.of("8h"),
                Card.of("9s"),
            ],
            winners=[PLAYER_2],
            winning_hands={PLAYER_2: HandResult(rank=HandRank.STRAIGHT, high_cards=[9], description="Straight")},
        )

    def test_wheel_straight_ace_low(self) -> None:
        """Test that in wheel straight, ace is treated as low."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("2s")],
                PLAYER_2: [Card.of("Kc"), Card.of("Qd")],
            },
            community_cards=[
                Card.of("3d"),
                Card.of("4c"),
                Card.of("5h"),
                Card.of("7s"),
                Card.of("9c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[5], description="Straight")},  # Wheel is 5-high
        )

    def test_almost_straight_vs_high_card(self) -> None:
        """Test that almost-straight is just high card."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Ks")],
                PLAYER_2: [Card.of("8c"), Card.of("7d")],
            },
            community_cards=[
                Card.of("Qd"),
                Card.of("Jc"),
                Card.of("9h"),  # Almost straight: A-K-Q-J-9 (missing 10)
                Card.of("4s"),
                Card.of("2c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13], description="High Card")},  # Ace high
        )

    def test_pair_vs_two_pair_kicker_comparison(self) -> None:
        """Test pair vs two pair comparison."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("As")],
                PLAYER_2: [Card.of("Kc"), Card.of("Qd")],
            },
            community_cards=[
                Card.of("Kh"),
                Card.of("Qs"),
                Card.of("7c"),
                Card.of("5h"),
                Card.of("3d"),
            ],
            winners=[PLAYER_2],
            winning_hands={PLAYER_2: HandResult(rank=HandRank.TWO_PAIR, high_cards=[13, 12], description="Two Pair")},
        )

    def test_two_pair_kicker_comparison(self) -> None:
        """Test two pair comparison by different pairs."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Ks")],
                PLAYER_2: [Card.of("Ac"), Card.of("Qd")],
            },
            community_cards=[
                Card.of("As"),
                Card.of("Kc"),
                Card.of("Qh"),  # Player 1: A-A-K-K, Player 2: A-A-Q-Q
                Card.of("8s"),
                Card.of("7d"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.TWO_PAIR, high_cards=[14, 13], description="Two Pair")},  # Kings beat Queens
        )

    def test_three_of_a_kind_kicker_comparison(self) -> None:
        """Test three of a kind comparison by kicker."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("8h"), Card.of("Ad")],
                PLAYER_2: [Card.of("8c"), Card.of("Kh")],
            },
            community_cards=[
                Card.of("8s"),
                Card.of("8d"),
                Card.of("5h"),
                Card.of("3s"),
                Card.of("2c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[8, 14], description="Three of a Kind")},
        )

    def test_full_house_comparison_by_trips_then_pair(self) -> None:
        """Test full house comparison by trips, then by pair."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kc")],
                PLAYER_2: [Card.of("Ac"), Card.of("Qs")],
            },
            community_cards=[
                Card.of("As"),
                Card.of("Ad"),
                Card.of("Kh"),  # Player 1: Aces full of Kings
                Card.of("Qc"),  # Player 2: Aces full of Queens
                Card.of("7d"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[14, 13], description="Full House")},  # Kings beat Queens
        )

    def test_flush_kicker_comparison(self) -> None:
        """Test flush comparison by multiple kickers."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kh")],
                PLAYER_2: [Card.of("As"), Card.of("Ks")],
            },
            community_cards=[
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("9h"),  # Player 1: A-K-Q-J-9 flush
                Card.of("Qs"),
                Card.of("Js"),  # Player 2: A-K-Q-J-8 flush (8 from community)
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush")},  # 9 beats 8
        )

    def test_royal_flush_vs_king_high_straight_flush(self) -> None:
        """Test royal flush vs king-high straight flush."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kh")],
                PLAYER_2: [Card.of("Ks"), Card.of("Qs")],
            },
            community_cards=[
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("10h"),  # Player 1: Royal flush
                Card.of("Js"),
                Card.of("10s"),  # Player 2: K-Q-J-T-9 straight flush
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush")},
        )

    def test_high_card_multiple_kicker_comparison(self) -> None:
        """Test high card comparison with multiple kickers."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Ks")],
                PLAYER_2: [Card.of("Ac"), Card.of("Qd")],
            },
            community_cards=[
                Card.of("Jh"),
                Card.of("10c"),
                Card.of("8s"),  # Player 1: A-K-J-T-8, Player 2: A-Q-J-T-8
                Card.of("5d"),
                Card.of("3h"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13], description="High Card")},  # King beats Queen
        )

    def test_royal_flush_spades(self) -> None:
        """Test royal flush in spades."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("As"), Card.of("Ks")],
                PLAYER_2: [Card.of("Ah"), Card.of("Kh")],
            },
            community_cards=[
                Card.of("Qs"),
                Card.of("Js"),
                Card.of("10s"),
                Card.of("9d"),
                Card.of("8c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush")},
        )

    def test_wheel_straight_flush(self) -> None:
        """Test wheel straight flush (A-2-3-4-5 suited)."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ac"), Card.of("2c")],
                PLAYER_2: [Card.of("Kh"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("3c"),
                Card.of("4c"),
                Card.of("5c"),
                Card.of("Jh"),
                Card.of("10h"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[5], description="Straight Flush")},  # Wheel straight flush is 5-high
        )

    def test_two_pair_comparison_by_higher_pair(self) -> None:
        """Test two pair comparison by higher pair."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Qd")],
                PLAYER_2: [Card.of("Jc"), Card.of("10h")],
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("Qh"),
                Card.of("Js"),
                Card.of("10d"),
                Card.of("5s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.TWO_PAIR, high_cards=[13, 12], description="Two Pair")},
        )

    def test_full_house_comparison_by_trips(self) -> None:
        """Test full house comparison by three of a kind rank."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Kd")],
                PLAYER_2: [Card.of("Qc"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("Qs"),
                Card.of("7h"),
                Card.of("7d"),
                Card.of("7c"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[13, 7], description="Full House")},
        )

    def test_four_of_a_kind_comparison_by_kicker(self) -> None:
        """Test four of a kind comparison by kicker."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kd")],
                PLAYER_2: [Card.of("Qc"), Card.of("Jh")],
            },
            community_cards=[
                Card.of("7s"),
                Card.of("7d"),
                Card.of("7c"),
                Card.of("7h"),
                Card.of("3s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[7, 14], description="Four of a Kind")},
        )

    def test_identical_high_card_tie(self) -> None:
        """Test identical high card hands result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Ks")],
                PLAYER_2: [Card.of("Ac"), Card.of("Kd")],
            },
            community_cards=[
                Card.of("Qd"),
                Card.of("Jc"),
                Card.of("9h"),  # Both players: A-K-Q-J-9
                Card.of("8c"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13], description="High Card"),
                PLAYER_2: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13], description="High Card"),
            },
        )

    def test_identical_three_of_a_kind_tie(self) -> None:
        """Test identical three of a kind hands result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("7h"), Card.of("Ac")],
                PLAYER_2: [Card.of("7c"), Card.of("As")],
            },
            community_cards=[
                Card.of("7s"),
                Card.of("7d"),
                Card.of("Kh"),  # Both players: 7-7-7-A-K
                Card.of("Qc"),
                Card.of("5d"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[7, 14], description="Three of a Kind"),
                PLAYER_2: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[7, 14], description="Three of a Kind"),
            },
        )

    def test_identical_two_pair_tie(self) -> None:
        """Test identical two pair hands result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Qs")],
                PLAYER_2: [Card.of("Ac"), Card.of("Jd")],
            },
            community_cards=[
                Card.of("As"),
                Card.of("Kc"),
                Card.of("Kh"),  # Both players: A-A-K-K
                Card.of("3d"),  # Both players have A-A-K-K-3
                Card.of("2c"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.TWO_PAIR, high_cards=[14, 13], description="Two Pair"),
                PLAYER_2: HandResult(rank=HandRank.TWO_PAIR, high_cards=[14, 13], description="Two Pair"),
            },
        )

    def test_identical_royal_flush_tie(self) -> None:
        """Test identical royal flushes result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2c"), Card.of("3d")],
                PLAYER_2: [Card.of("4s"), Card.of("5c")],
            },
            community_cards=[
                Card.of("Ah"),
                Card.of("Kh"),
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("10h"),  # Both players have royal flush from community
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie - both have royal flush
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
                PLAYER_2: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
            },
        )

    def test_identical_straight_flush_tie(self) -> None:
        """Test identical straight flushes result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2c"), Card.of("3d")],
                PLAYER_2: [Card.of("4s"), Card.of("5c")],
            },
            community_cards=[
                Card.of("9h"),
                Card.of("8h"),
                Card.of("7h"),
                Card.of("6h"),
                Card.of("5h"),  # Both players have 9-high straight flush from community
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[9], description="Straight Flush"),
                PLAYER_2: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[9], description="Straight Flush"),
            },
        )

    def test_identical_four_of_a_kind_tie(self) -> None:
        """Test identical four of a kind with same kicker results in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2h"), Card.of("3s")],
                PLAYER_2: [Card.of("4c"), Card.of("5d")],
            },
            community_cards=[
                Card.of("7h"),
                Card.of("7s"),
                Card.of("7d"),
                Card.of("7c"),  # Both players have quad 7s
                Card.of("Ah"),  # Both have Ace kicker
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[7, 14], description="Four of a Kind"),
                PLAYER_2: HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[7, 14], description="Four of a Kind"),
            },
        )

    def test_identical_full_house_tie(self) -> None:
        """Test identical full houses result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2h"), Card.of("3s")],
                PLAYER_2: [Card.of("4c"), Card.of("5d")],
            },
            community_cards=[
                Card.of("Ah"),
                Card.of("As"),
                Card.of("Ad"),
                Card.of("Kc"),
                Card.of("Kh"),  # Both players have Aces full of Kings
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[14, 13], description="Full House"),
                PLAYER_2: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[14, 13], description="Full House"),
            },
        )

    def test_identical_flush_tie(self) -> None:
        """Test identical flushes result in a tie."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2c"), Card.of("3d")],
                PLAYER_2: [Card.of("4s"), Card.of("5c")],
            },
            community_cards=[
                Card.of("Ah"),
                Card.of("Kh"),
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("9h"),  # Both players have A-K-Q-J-9 flush
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush"),
                PLAYER_2: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush"),
            },
        )

    def test_straight_flush_comparison_different_ranks(self) -> None:
        """Test straight flush comparison with different high cards."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("9h"), Card.of("8h")],
                PLAYER_2: [Card.of("8s"), Card.of("7s")],
            },
            community_cards=[
                Card.of("7h"),
                Card.of("6h"),
                Card.of("5h"),  # Player 1: 9-high straight flush
                Card.of("6s"),
                Card.of("5s"),  # Player 2: 8-high straight flush
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[9], description="Straight Flush")},
        )

    def test_wheel_straight_flush_vs_higher_straight_flush(self) -> None:
        """Test wheel straight flush vs higher straight flush."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ac"), Card.of("2c")],
                PLAYER_2: [Card.of("6h"), Card.of("7h")],
            },
            community_cards=[
                Card.of("3c"),
                Card.of("4c"),
                Card.of("5c"),  # Player 1: wheel straight flush (5-high)
                Card.of("8h"),
                Card.of("9h"),  # Player 2: 9-high straight flush
            ],
            winners=[PLAYER_1],  # Player 1 has wheel straight flush (A-2-3-4-5)
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[5], description="Straight Flush")},
        )

    def test_four_of_a_kind_comparison_different_quads(self) -> None:
        """Test four of a kind vs four of a kind with different quad ranks."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Kd")],
                PLAYER_2: [Card.of("Qc"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("Ks"),  # Player 1: quad Kings
                Card.of("Qs"),
                Card.of("Qd"),  # Player 2: quad Queens
                Card.of("Ah"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[13, 14], description="Four of a Kind")},
        )

    def test_full_house_same_trips_different_pairs(self) -> None:
        """Test full house comparison with same trips but different pairs."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("8h"), Card.of("Kd")],
                PLAYER_2: [Card.of("8c"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("8s"),
                Card.of("8d"),  # Both players have trip 8s
                Card.of("Kc"),  # Player 1: 8s full of Kings
                Card.of("Qs"),  # Player 2: 8s full of Queens
                Card.of("7h"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[8, 13], description="Full House")},
        )

    def test_full_house_different_trips_ranks(self) -> None:
        """Test full house comparison with significantly different trips ranks."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Ad")],
                PLAYER_2: [Card.of("7c"), Card.of("7h")],
            },
            community_cards=[
                Card.of("Ac"),  # Player 1: trip Aces
                Card.of("7s"),  # Player 2: trip 7s
                Card.of("3h"),
                Card.of("3d"),  # Both players have pair of 3s
                Card.of("Ks"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[14, 3], description="Full House")},
        )

    def test_three_of_a_kind_multiple_kicker_comparison(self) -> None:
        """Test three of a kind with multiple kicker comparisons when first kicker ties."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("9h"), Card.of("Kd")],
                PLAYER_2: [Card.of("9c"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("9s"),
                Card.of("9d"),  # Both players have trip 9s
                Card.of("Ac"),  # Both have Ace as first kicker
                Card.of("8h"),
                Card.of("7s"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Both have same hand: trip 9s with A-8 kickers
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[9, 14], description="Three of a Kind"),
                PLAYER_2: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[9, 14], description="Three of a Kind"),
            },
        )

    def test_pair_comparison_third_kicker(self) -> None:
        """Test pair comparison going to third kicker."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("10h"), Card.of("9d")],
                PLAYER_2: [Card.of("10c"), Card.of("8h")],
            },
            community_cards=[
                Card.of("10s"),  # Both players have pair of 10s
                Card.of("Ac"),  # Both have Ace as first kicker
                Card.of("Kh"),  # Both have King as second kicker
                Card.of("7s"),
                Card.of("6d"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Both have same hand: pair of 10s with A-K-7 kickers
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.PAIR, high_cards=[10, 14], description="Pair"),
                PLAYER_2: HandResult(rank=HandRank.PAIR, high_cards=[10, 14], description="Pair"),
            },
        )

    def test_two_pair_kicker_tiebreaker(self) -> None:
        """Test two pair with kicker tiebreaker when both pairs are identical."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Jh"), Card.of("Jd")],
                PLAYER_2: [Card.of("10c"), Card.of("10h")],
            },
            community_cards=[
                Card.of("As"),
                Card.of("Ac"),  # Both players have pair of Aces
                Card.of("Kh"),  # Player 1: A-A-J-J-K, Player 2: A-A-T-T-K
                Card.of("9s"),
                Card.of("8d"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.TWO_PAIR, high_cards=[14, 11], description="Two Pair")},  # Jacks beat Tens
        )

    def test_boundary_lowest_vs_slightly_higher_high_card(self) -> None:
        """Test lowest possible high card vs slightly higher."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2h"), Card.of("3d")],
                PLAYER_2: [Card.of("2c"), Card.of("4h")],
            },
            community_cards=[
                Card.of("5s"),
                Card.of("7c"),
                Card.of("9h"),  # Player 1: K-J-9-7-5, Player 2: K-J-9-7-5 (both use community cards)
                Card.of("Jd"),
                Card.of("Ks"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Both have identical hands: K-J-9-7-5
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[13, 11], description="High Card"),
                PLAYER_2: HandResult(rank=HandRank.HIGH_CARD, high_cards=[13, 11], description="High Card"),
            },
        )

    def test_boundary_lowest_pair_vs_higher_pair(self) -> None:
        """Test lowest possible pair vs next higher pair."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2h"), Card.of("2d")],
                PLAYER_2: [Card.of("3c"), Card.of("3h")],
            },
            community_cards=[
                Card.of("As"),
                Card.of("Kc"),
                Card.of("Qh"),  # Player 1: 2-2-A-K-Q, Player 2: 3-3-A-K-Q
                Card.of("7d"),
                Card.of("5s"),
            ],
            winners=[PLAYER_2],
            winning_hands={PLAYER_2: HandResult(rank=HandRank.PAIR, high_cards=[3, 14], description="Pair")},  # Pair of 3s beats pair of 2s
        )

    def test_broadway_straight_vs_other_ace_high_straight(self) -> None:
        """Test Broadway straight (T-J-Q-K-A) vs other ace-high straight."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kd")],
                PLAYER_2: [Card.of("Ac"), Card.of("9h")],
            },
            community_cards=[
                Card.of("Qs"),
                Card.of("Jc"),
                Card.of("10h"),  # Player 1: Broadway straight (A-K-Q-J-T)
                Card.of("8d"),  # Player 2: No straight, just Ace high
                Card.of("7s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[14], description="Straight")},  # Broadway straight
        )

    def test_straight_comparison_broadway_vs_king_high(self) -> None:
        """Test Broadway straight vs King-high straight."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kd")],
                PLAYER_2: [Card.of("Kc"), Card.of("Qh")],
            },
            community_cards=[
                Card.of("Qs"),
                Card.of("Jc"),
                Card.of("10h"),  # Player 1: A-K-Q-J-T, Player 2: K-Q-J-T-9
                Card.of("9d"),
                Card.of("8s"),
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[14], description="Straight")},  # Ace-high beats King-high
        )

    def test_flush_comparison_fourth_kicker(self) -> None:
        """Test flush comparison going to fourth kicker."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("8h")],
                PLAYER_2: [Card.of("As"), Card.of("7s")],
            },
            community_cards=[
                Card.of("Kh"),
                Card.of("Qh"),
                Card.of("6h"),  # Player 1: A-K-Q-8-6 flush
                Card.of("Ks"),
                Card.of("Qs"),  # Player 2: A-K-Q-7-6 flush
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush")},  # 8 beats 7 as fourth kicker
        )

    def test_flush_comparison_fifth_kicker(self) -> None:
        """Test flush comparison going to fifth kicker."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("5h")],
                PLAYER_2: [Card.of("As"), Card.of("4s")],
            },
            community_cards=[
                Card.of("Kh"),
                Card.of("Qh"),
                Card.of("Jh"),  # Player 1: A-K-Q-J-5 flush
                Card.of("Ks"),
                Card.of("Qs"),  # Player 2: A-K-Q-J-4 flush
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush")},  # 5 beats 4 as fifth kicker
        )

    def test_flush_comparison_very_close_kickers(self) -> None:
        """Test flush comparison with very close kickers."""
        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("10h"), Card.of("9h")],
                PLAYER_2: [Card.of("10s"), Card.of("8s")],
            },
            community_cards=[
                Card.of("Ah"),
                Card.of("Kh"),
                Card.of("7h"),  # Player 1: A-K-T-9-7 flush
                Card.of("As"),
                Card.of("Ks"),  # Player 2: A-K-T-8-7 flush
            ],
            winners=[PLAYER_1],
            winning_hands={PLAYER_1: HandResult(rank=HandRank.FLUSH, high_cards=[14], description="Flush")},  # 9 beats 8 as fourth kicker
        )
