"""Extended hand evaluation tests for Texas Hold'em.


Adds missing test cases to the existing hand ranking tests to ensure complete coverage.
"""

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

    players_to_act = list(hole_cards.keys())

    current_player = test.state.current_player_id

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


class TestHandEvaluationExtended:
    """Extended hand evaluation tests to cover missing cases."""

    def test_royal_flush_spades_vs_hearts(self) -> None:
        """Test royal flush comparison (should tie)."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("As"), Card.of("Ks")],
                PLAYER_2: [Card.of("Ah"), Card.of("10h")],
            },
            community_cards=[
                Card.of("Qs"),
                Card.of("Js"),
                Card.of("10s"),
                Card.of("Qh"),
                Card.of("Jh"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
                PLAYER_2: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
            },
        )

    def test_straight_flush_vs_four_of_a_kind(self) -> None:
        """Test straight flush beats four of a kind."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("9h"), Card.of("8h")],
                PLAYER_2: [Card.of("Ac"), Card.of("Ad")],
            },
            community_cards=[
                Card.of("7h"),
                Card.of("6h"),
                Card.of("5h"),
                Card.of("As"),
                Card.of("Ah"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[9], description="Straight Flush"),
                PLAYER_2: HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[14, 7], description="Four of a Kind"),
            },
        )

    def test_wheel_straight_flush_vs_king_high_straight_flush(self) -> None:
        """Test wheel straight flush vs king high straight flush."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("2h")],  # Wheel straight flush
                PLAYER_2: [Card.of("Ks"), Card.of("9s")],  # King high straight flush
            },
            community_cards=[
                Card.of("3h"),
                Card.of("4h"),
                Card.of("5h"),
                Card.of("Qs"),
                Card.of("Js"),
            ],
            winners=[PLAYER_1],  # Wheel straight flush wins
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[5], description="Straight Flush"),
                PLAYER_2: HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[13], description="Straight Flush"),
            },
        )

    def test_full_house_trips_comparison(self) -> None:
        """Test full house comparison by trips rank."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Kd")],  # Kings full of 7s
                PLAYER_2: [Card.of("Qh"), Card.of("Qd")],  # Queens full of 7s
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("Qc"),
                Card.of("7h"),
                Card.of("7d"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[13, 7], description="Full House"),
                PLAYER_2: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[12, 7], description="Full House"),
            },
        )

    def test_full_house_pair_comparison(self) -> None:
        """Test full house comparison by pair rank when trips are equal."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("8h"), Card.of("8d")],  # Kings full of 8s
                PLAYER_2: [Card.of("7h"), Card.of("7d")],  # Kings full of 7s
            },
            community_cards=[
                Card.of("Kc"),
                Card.of("Ks"),
                Card.of("Kh"),
                Card.of("2c"),
                Card.of("3s"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[13, 8], description="Full House"),
                PLAYER_2: HandResult(rank=HandRank.FULL_HOUSE, high_cards=[13, 7], description="Full House"),
            },
        )

    def test_flush_all_five_kickers(self) -> None:
        """Test flush comparison using all five kickers."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("9h"), Card.of("5h")],  # A-K-9-5-2 flush in hearts
                PLAYER_2: [Card.of("8s"), Card.of("6s")],  # Q-J-8-6-4 flush in spades
            },
            community_cards=[Card.of("Ah"), Card.of("Kh"), Card.of("4s"), Card.of("Js"), Card.of("3s")],
            winners=[PLAYER_2],  # Flush beats high card
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13, 11, 9, 5], description="High Card"),
                PLAYER_2: HandResult(rank=HandRank.FLUSH, high_cards=[11, 8, 6, 4, 3], description="Flush"),
            },
        )

    def test_broadway_straight_vs_king_high_straight(self) -> None:
        """Test broadway straight vs king high straight."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kh")],  # Broadway straight
                PLAYER_2: [Card.of("Kd"), Card.of("Qd")],  # King high straight
            },
            community_cards=[
                Card.of("Qc"),
                Card.of("Jc"),
                Card.of("10c"),
                Card.of("9s"),
                Card.of("2h"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[14], description="Straight"),
                PLAYER_2: HandResult(rank=HandRank.STRAIGHT, high_cards=[13], description="Straight"),
            },
        )

    def test_three_of_a_kind_multiple_kickers(self) -> None:
        """Test three of a kind with multiple kicker comparison."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Kh"), Card.of("Ah")],  # Trip 7s with A-K kickers
                PLAYER_2: [Card.of("Qh"), Card.of("Jh")],  # Trip 7s with Q-J kickers
            },
            community_cards=[
                Card.of("7h"),
                Card.of("7d"),
                Card.of("7c"),
                Card.of("2s"),
                Card.of("3s"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[7, 14, 13], description="Three of a Kind"),
                PLAYER_2: HandResult(rank=HandRank.THREE_OF_A_KIND, high_cards=[7, 12, 11], description="Three of a Kind"),
            },
        )

    def test_two_pair_kicker_tiebreaker(self) -> None:
        """Test two pair with kicker tiebreaker."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Qh")],  # A-K two pair with Q kicker
                PLAYER_2: [Card.of("Ad"), Card.of("Jd")],  # A-K two pair with J kicker
            },
            community_cards=[
                Card.of("Ac"),
                Card.of("Kc"),
                Card.of("Kh"),
                Card.of("8h"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1],
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.TWO_PAIR, high_cards=[14, 13, 12], description="Two Pair"),
                PLAYER_2: HandResult(rank=HandRank.TWO_PAIR, high_cards=[14, 13, 11], description="Two Pair"),
            },
        )

    def test_pair_third_kicker_comparison(self) -> None:
        """Test pair comparison using third kicker."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Jh")],  # Pair of Aces with K-Q-J kickers
                PLAYER_2: [Card.of("Ad"), Card.of("10d")],  # Pair of Aces with K-Q-10 kickers
            },
            community_cards=[
                Card.of("Ac"),
                Card.of("Kc"),
                Card.of("Qh"),
                Card.of("8h"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1],  # J kicker beats 10 kicker
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.PAIR, high_cards=[14, 13, 12, 11], description="Pair"),
                PLAYER_2: HandResult(rank=HandRank.PAIR, high_cards=[14, 13, 12, 10], description="Pair"),
            },
        )

    def test_high_card_five_kicker_comparison(self) -> None:
        """Test high card comparison using all five kickers."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("9h")],  # A-K-Q-J-9 high
                PLAYER_2: [Card.of("Ad"), Card.of("8d")],  # A-K-Q-J-8 high
            },
            community_cards=[
                Card.of("Qc"),
                Card.of("Jc"),
                Card.of("Kc"),
                Card.of("7h"),
                Card.of("2s"),
            ],
            winners=[PLAYER_1],  # 9 beats 8 as fifth kicker
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13, 12, 11, 9], description="High Card"),
                PLAYER_2: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13, 12, 11, 8], description="High Card"),
            },
        )

    def test_identical_hands_complete_tie(self) -> None:
        """Test completely identical hands result in tie."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("2h"), Card.of("3h")],  # Both use board
                PLAYER_2: [Card.of("2d"), Card.of("3d")],  # Both use board
            },
            community_cards=[
                Card.of("Ah"),
                Card.of("Kh"),
                Card.of("Qh"),
                Card.of("Jh"),
                Card.of("10h"),
            ],
            winners=[PLAYER_1, PLAYER_2],  # Complete tie
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
                PLAYER_2: HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[14], description="Royal Flush"),
            },
        )

    def test_almost_straight_vs_high_card(self) -> None:
        """Test that almost-straight is just high card."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("Ah"), Card.of("Kh")],  # A-K-Q-J-9 (missing 10)
                PLAYER_2: [Card.of("8d"), Card.of("7d")],  # 8-7-6-4-3 (missing 5)
            },
            community_cards=[
                Card.of("Qc"),
                Card.of("Jc"),
                Card.of("9h"),
                Card.of("6s"),
                Card.of("4s"),  # Changed 5s to 4s to break Player 2's straight
            ],
            winners=[PLAYER_1],  # Ace high beats 8 high
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.HIGH_CARD, high_cards=[14, 13, 12, 11, 9], description="High Card"),
                PLAYER_2: HandResult(rank=HandRank.HIGH_CARD, high_cards=[12, 11, 9, 8, 7], description="High Card"),
            },
        )

    def test_wheel_vs_broadway_straight(self) -> None:
        """Test wheel straight vs broadway straight."""

        _test_rank(
            hole_cards={
                PLAYER_1: [Card.of("3h"), Card.of("2h")],  # Wheel (A-2-3-4-5)
                PLAYER_2: [Card.of("Kd"), Card.of("Qd")],  # Broadway (A-K-Q-J-10)
            },
            community_cards=[
                Card.of("As"),
                Card.of("4c"),
                Card.of("5h"),
                Card.of("Jc"),
                Card.of("10s"),
            ],
            winners=[PLAYER_2],  # Broadway beats wheel
            winning_hands={
                PLAYER_1: HandResult(rank=HandRank.STRAIGHT, high_cards=[5], description="Straight"),
                PLAYER_2: HandResult(rank=HandRank.STRAIGHT, high_cards=[14], description="Straight"),
            },
        )
