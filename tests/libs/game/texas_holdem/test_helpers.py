"""Test helpers for Texas Hold'em poker tests."""

from __future__ import annotations

from typing import Any

from game_api import EventCollector, GameId, GameType, PlayerMove
from pydantic import BaseModel

from common.core.app_error import AppException
from common.ids import AgentVersionId, PlayerId
from common.utils.tsid import TSID
from common.utils.utils import is_dict, is_list
from libs.game.texas_holdem.texas_holdem_api import (
    BettingRound,
    Card,
    PlayerStatus,
    TexasHoldemAction,
    TexasHoldemConfig,
    TexasHoldemEvent,
    TexasHoldemMoveData,
    TexasHoldemPlayer,
    TexasHoldemState,
)
from libs.game.texas_holdem.texas_holdem_env import TexasHoldemEnv

# Create PLAYER constants for consistent testing
PLAYER_1 = AgentVersionId(TSID(0))
PLAYER_2 = AgentVersionId(TSID(1))
PLAYER_3 = AgentVersionId(TSID(2))
PLAYER_4 = AgentVersionId(TSID(3))
PLAYER_5 = AgentVersionId(TSID(4))

# Create consistent PLAYER_ID constants for testing
PLAYER_ID_1 = PlayerId(TSID(0))
PLAYER_ID_2 = PlayerId(TSID(1))
PLAYER_ID_3 = PlayerId(TSID(2))
PLAYER_ID_4 = PlayerId(TSID(3))
PLAYER_ID_5 = PlayerId(TSID(4))

__all__ = [
    "PLAYER_1",
    "PLAYER_2",
    "PLAYER_3",
    "PLAYER_4",
    "PLAYER_5",
    "PLAYER_ID_1",
    "PLAYER_ID_2",
    "PLAYER_ID_3",
    "PLAYER_ID_4",
    "PLAYER_ID_5",
    "PokerTest",
    "TexasHoldemPlayerDiff",
    "TexasHoldemStateDiff",
]


class PokerTest:
    """Instance-based test class for testing poker games through TexasHoldemRuleManager.


    Each test should create its own instance using PokerTest.setup().

    The test instance manages game state and config internally.

    """

    state: TexasHoldemState

    config: TexasHoldemConfig

    env: TexasHoldemEnv

    last_state_diff: TexasHoldemStateDiff | None = None

    def __init__(self, state: TexasHoldemState, config: TexasHoldemConfig, env: TexasHoldemEnv, agent_ids: list[AgentVersionId] | None = None) -> None:
        """Initialize the poker test helper with state and config.


        Use PokerTest.setup() instead of calling this directly.

        """

        self.state = state

        self.config = config

        self.env = env

        self.agent_ids = agent_ids or []

    @classmethod
    def create(
        cls,
        # Game configuration
        num_players: int = 5,
        small_blind: int = 5,
        big_blind: int = 10,
        starting_chips: int = 1000,
        min_raise: int | None = None,
        max_raise: int | None = None,
        # Player overrides
        chips: dict[AgentVersionId, int] | None = None,
        current_bets: dict[AgentVersionId, int] | None = None,
        total_bets: dict[AgentVersionId, int] | None = None,
        hole_cards: dict[AgentVersionId, list[Card]] | None = None,
        # State overrides (for advanced testing scenarios)
        betting_round: BettingRound | None = None,
        current_player_id: AgentVersionId | None = None,
        community_cards: list[Card] | None = None,
        pot: int | None = None,
        current_bet: int | None = None,
        dealer_position: int | None = -3,
        deck: list[Card] | None = None,
        winners: list[AgentVersionId] | None = None,
        winning_hands: dict[AgentVersionId, Any] | None = None,
    ) -> PokerTest:
        """Set up a poker test helper.


        Args:
            num_players: Number of players (default: 5)

            betting_round: Current betting round (default: PREFLOP)

            small_blind: Small blind amount (default: 5)

            big_blind: Big blind amount (default: 10)

            starting_chips: Starting chips per player (default: 1000)

            ante: Ante amount (default: 0)

            min_raise: Minimum raise amount (default: None)

            max_raise: Maximum raise amount (default: None)


            # Player overrides (applied after production init)

            chips: Override chips for specific players {PLAYER_1: 500}

            current_bets: Override current bets for specific players

            total_bets: Override total bets for specific players

            hole_cards: Override hole cards for specific players {PLAYER_1: [card1, card2]}


            # State overrides (for advanced testing scenarios only)

            current_player_id: Current player ID (default: from production init)

            community_cards: Community cards (default: from production init)

            pot: Pot amount (default: from production init)

            current_bet: Current bet amount (default: from production init)

            dealer_position: Dealer position (default: from production init)

            deck: Deck of cards (default: from production init)

            winners: Winners list (default: [])

            winning_hands: Winning hands dict (default: {})


        Returns:
            PokerTest instance with configured state and config

        """

        print(f"DEBUG: PokerTest.create called with num_players={num_players}")
        print(f"DEBUG: current_bets={current_bets}, total_bets={total_bets}, hole_cards={hole_cards}")

        if num_players < 2:
            raise ValueError("Number of players must be at least 2")

        if num_players > 5:
            raise ValueError("Number of players must be at most 5")

        # Create config

        config = TexasHoldemConfig(
            env=GameType.TEXAS_HOLDEM,
            max_players=5,
            min_players=2,
            small_blind=small_blind,
            big_blind=big_blind,
            starting_chips=starting_chips,
            starting_chips_override_for_test=chips,
            default_dealer_position=(dealer_position % num_players) if dealer_position is not None else 0,
            min_raise=min_raise,
            max_raise=max_raise,
        )

        env = TexasHoldemEnv(config)

        # Use predefined player constants for consistency with tests

        predefined_players = [PLAYER_1, PLAYER_2, PLAYER_3, PLAYER_4, PLAYER_5]
        player_ids = predefined_players[:num_players]

        event_collector = EventCollector[TexasHoldemEvent]()

        # Create basic game state without players
        from common.ids import GameId
        from common.utils.tsid import TSID

        game_id = GameId(TSID.create())
        state = env.new_game(game_id, event_collector)

        # Use consistent player IDs for testing
        predefined_player_ids = [PLAYER_ID_1, PLAYER_ID_2, PLAYER_ID_3, PLAYER_ID_4, PLAYER_ID_5]
        actual_player_ids = predefined_player_ids[:num_players]
        for i, player_id in enumerate(actual_player_ids):
            from common.ids import AgentVersionId

            agent_version_id = AgentVersionId(TSID.create())
            env.join_player(state, player_id, event_collector, agent_version_id, f"Player {i + 1}")

        # Create agent to player mapping for test setup
        # This maps agent IDs (used for test setup) to actual player IDs (used in game state)
        agent_to_player_mapping = {agent_id: player_id for agent_id, player_id in zip(player_ids, actual_player_ids, strict=False)}

        print(f"DEBUG: Created agent_to_player_mapping: {agent_to_player_mapping}")
        print(f"DEBUG: State after adding players: players={[p.player_id for p in state.players]}")

        # Apply overrides using agent IDs for convenience, but map to actual player IDs

        if chips:
            for agent_id, chip_amount in chips.items():
                if agent_id in agent_to_player_mapping:
                    player_id = agent_to_player_mapping[agent_id]
                    for player in state.players:
                        if player.player_id == player_id:
                            player.chips = chip_amount
                            break

        if current_bets:
            for agent_id, bet_amount in current_bets.items():
                if agent_id in agent_to_player_mapping:
                    player_id = agent_to_player_mapping[agent_id]
                    for player in state.players:
                        if player.player_id == player_id:
                            player.current_bet = bet_amount
                            break

        if total_bets:
            for agent_id, bet_amount in total_bets.items():
                if agent_id in agent_to_player_mapping:
                    player_id = agent_to_player_mapping[agent_id]
                    for player in state.players:
                        if player.player_id == player_id:
                            player.total_bet = bet_amount
                            break

        print(f"DEBUG: Final state: current_player_id={state.current_player_id}, players={len(state.players)}")

        # Initialize the first round after adding players
        if len(state.players) >= 2:  # Need at least 2 players to start a round
            # Initialize round-specific state including blinds and positions
            env._init_new_round(state, event_collector)
            print(
                f"DEBUG: After _init_new_round: pot={state.pot}, current_bet={state.current_bet}, small_blind_pos={state.small_blind_position}, big_blind_pos={state.big_blind_position}"
            )

        # Apply state overrides AFTER starting the first hand
        # This allows tests to override the dealt cards and other state

        if hole_cards:
            for agent_id, cards in hole_cards.items():
                if agent_id in agent_to_player_mapping:
                    player_id = agent_to_player_mapping[agent_id]
                    for player in state.players:
                        if player.player_id == player_id:
                            player.hole_cards = cards
                            break

        if betting_round is not None:
            state.betting_round = betting_round

        if current_player_id is not None and current_player_id in agent_to_player_mapping:
            state.current_player_id = agent_to_player_mapping[current_player_id]

        if community_cards is not None:
            state.community_cards = community_cards

        if pot is not None:
            state.pot = pot

        if current_bet is not None:
            state.current_bet = current_bet

        if deck is not None:
            state.deck = deck

        if winners is not None:
            # Map agent IDs to player IDs for winners
            mapped_winners = []
            for agent_id in winners:
                if agent_id in agent_to_player_mapping:
                    mapped_winners.append(agent_to_player_mapping[agent_id])
            state.winners = mapped_winners

        if winning_hands is not None:
            # Map agent IDs to player IDs for winning hands
            mapped_winning_hands = {}
            for agent_id, hand in winning_hands.items():
                if agent_id in agent_to_player_mapping:
                    mapped_winning_hands[agent_to_player_mapping[agent_id]] = hand
            state.winning_hands = mapped_winning_hands

        return cls(state, config, env, player_ids)

    def process_move(
        self,
        player_id: AgentVersionId,
        action: TexasHoldemAction,
        amount: int | None = None,
        expected_state_diff: TexasHoldemStateDiff | None = None,
        exclude_fields: set[str] | None = {"players.hole_cards", "deck", "community_cards"},  # noqa: B006
    ) -> None:
        """Process a poker move through the TexasHoldemRuleManager.

        Args:
            player_id: The agent ID of the player making the move (for test convenience)
            action: The action to take
            amount: The amount for bet/raise actions
            expected_state_diff: Expected state changes (optional)
            exclude_fields: Fields to exclude from state diff comparison

        """
        # Map agent ID to actual player ID used in game state
        actual_player_id = None
        for i, agent_id in enumerate(self.agent_ids):
            if agent_id == player_id:
                if i < len(self.state.players):
                    actual_player_id = self.state.players[i].player_id
                break

        if actual_player_id is None:
            raise ValueError(f"Could not find player ID for agent {player_id}")

        old_state = self.state

        move_data = TexasHoldemMoveData(action=action, amount=amount)
        move = PlayerMove(player_id=actual_player_id, data=move_data)

        try:
            event_collector = EventCollector[TexasHoldemEvent]()
            self.env.apply_move(self.state, move, event_collector)
            self.last_state_diff = self._compute_state_diff(old_state, self.state)

            if expected_state_diff is not None:
                self.assert_state_diff_matches(expected_state_diff, exclude_fields)

        except AppException as e:
            print(f"Move failed with error: {e}")
            raise

    def process_move_error(
        self,
        player_id: AgentVersionId,
        action: TexasHoldemAction,
        amount: int | None = None,
        expected_error: Any = None,
    ) -> AppException:
        """Process a poker move that is expected to fail.

        Args:
            player_id: The agent ID of the player making the move
            action: The action to take
            amount: The amount for bet/raise actions
            expected_error: Expected error type or message

        Returns:
            The AppException that was raised
        """
        # Map agent ID to actual player ID used in game state
        actual_player_id = None
        for i, agent_id in enumerate(self.agent_ids):
            if agent_id == player_id:
                if i < len(self.state.players):
                    actual_player_id = self.state.players[i].player_id
                break

        if actual_player_id is None:
            raise ValueError(f"Could not find player ID for agent {player_id}")

        move_data = TexasHoldemMoveData(action=action, amount=amount)
        move = PlayerMove(player_id=actual_player_id, data=move_data)

        try:
            event_collector = EventCollector[TexasHoldemEvent]()
            self.env.apply_move(self.state, move, event_collector)
            raise AssertionError(f"Expected move to fail but it succeeded: {action} by {player_id}")
        except AppException as e:
            if expected_error is not None:
                # You can add more specific error checking here if needed
                pass
            return e

    def assert_state(self, expected_state: TexasHoldemState) -> None:
        """Assert that the current state matches the expected state.

        Args:
            expected_state: Expected game state
        """
        # Compare states by converting to dict and excluding dynamic fields
        actual_dict = self.state.model_dump()
        expected_dict = expected_state.model_dump()

        # Remove fields that are expected to be different (like game_id, deck)
        dynamic_fields = {"game_id", "deck"}
        for field in dynamic_fields:
            actual_dict.pop(field, None)
            expected_dict.pop(field, None)

        assert actual_dict == expected_dict, f"State mismatch.\nExpected: {expected_dict}\nActual: {actual_dict}"

    def assert_state_change(self, expected_diff: TexasHoldemStateDiff) -> None:
        """Assert that the last state change matches the expected diff.

        Args:
            expected_diff: Expected state diff
        """
        self.assert_state_diff_matches(expected_diff)

    def is_game_finished(self) -> bool:
        """Check if the game is finished.

        Returns:
            True if the game is finished, False otherwise
        """
        return self.state.is_finished

    def _convert_expected_state_diff(self, expected: TexasHoldemStateDiff) -> TexasHoldemStateDiff:
        """Convert expected state diff from AgentVersionId keys to PlayerId keys.

        Args:
            expected: Expected state diff with AgentVersionId keys

        Returns:
            State diff with PlayerId keys
        """
        # Create agent to player mapping
        agent_to_player_mapping = {}
        for i, agent_id in enumerate(self.agent_ids):
            if i < len(self.state.players):
                agent_to_player_mapping[agent_id] = self.state.players[i].player_id

        # Convert the expected diff
        kwargs = {}

        # Handle all non-player fields
        for field_name, value in expected.model_dump(exclude_none=True).items():
            if field_name == "players":
                continue
            if field_name == "current_player_id" and isinstance(value, str):
                # Convert current_player_id from AgentVersionId to PlayerId
                if value in agent_to_player_mapping:
                    kwargs[field_name] = agent_to_player_mapping[value]
                else:
                    kwargs[field_name] = value
            else:
                kwargs[field_name] = value

        # Handle players field - convert keys from AgentVersionId to PlayerId
        if expected.players:
            converted_players = {}
            for agent_id, player_diff in expected.players.items():
                if agent_id in agent_to_player_mapping:
                    player_id = agent_to_player_mapping[agent_id]
                    converted_players[player_id] = player_diff
                else:
                    # If no mapping found, keep original key (shouldn't happen in normal tests)
                    converted_players[agent_id] = player_diff
            kwargs["players"] = converted_players

        return TexasHoldemStateDiff(**kwargs)

    def assert_state_diff_matches(
        self,
        expected: TexasHoldemStateDiff,
        exclude_fields: set[str] | None = None,
    ) -> None:
        """Assert that the last state diff matches the expected diff.

        Args:
            expected: Expected state diff
            exclude_fields: Fields to exclude from comparison (e.g., {"deck", "players.hole_cards"})

        """
        if self.last_state_diff is None:
            raise ValueError("No state diff available. Call process_move() first.")

        actual = self.last_state_diff

        # Convert expected diff from AgentVersionId keys to PlayerId keys
        expected_converted = self._convert_expected_state_diff(expected)

        # Convert to dicts for comparison
        expected_dump = expected_converted.to_dict()
        actual_dump = actual.to_dict()

        # Remove excluded fields
        if exclude_fields:
            self._remove_nested_fields(expected_dump, exclude_fields)
            self._remove_nested_fields(actual_dump, exclude_fields)

        print(f"Expected state diff: {expected_dump}")
        print(f"Actual state diff:   {actual_dump}")

        assert actual_dump == expected_dump, f"State mismatch.\nExpected: {expected_dump}\nActual:   {actual_dump}"

    def _remove_nested_fields(self, data: dict[str, Any], fields: set[str]) -> None:
        for field in list(fields):
            if "." in field:
                # Handle nested field exclusion like "players.chips"

                parent, child = field.split(".", 1)

                if parent in data:
                    if is_dict(data[parent]):
                        for key in list(data[parent].keys()):
                            if isinstance(data[parent][key], dict) and child in data[parent][key]:
                                data[parent][key].pop(child, None)

                                # Remove empty player diffs

                                if not data[parent][key]:
                                    data[parent].pop(key, None)

                    elif is_list(data[parent]):
                        for item in data[parent]:
                            if is_dict(item) and child in item:
                                item.pop(child, None)

                                # Remove empty player diffs

                                if not item:
                                    data[parent].remove(item)

                    else:
                        raise ValueError(f"Unsupported type for field {field}: {type(data[parent])}")

                    # Remove empty players dict

                    if not data[parent]:
                        data.pop(parent, None)

            else:
                # Handle top-level field exclusion

                data.pop(field, None)

    def _compute_state_diff(self, old: TexasHoldemState, new: TexasHoldemState) -> TexasHoldemStateDiff:
        def serialize(value: Any) -> Any:
            # Use pydantic dumps for BaseModel, and recursively for lists of BaseModels

            if isinstance(value, BaseModel):
                return value.model_dump()

            if is_list(value):
                return [serialize(v) for v in value]

            if is_dict(value):
                return {k: serialize(v) for k, v in value.items()}

            return value

        kwargs: dict[str, Any] = {}

        # Special handling for players: compute per-player diffs by id

        old_players = {p.player_id: p for p in old.players}

        new_players = {p.player_id: p for p in new.players}

        players_diff: dict[PlayerId, TexasHoldemPlayerDiff] = {}

        for pid, new_p in new_players.items():
            old_p = old_players.get(pid)

            if old_p is None:
                # Include all fields for a new player

                pd = TexasHoldemPlayerDiff()

                for fname in TexasHoldemPlayer.model_fields:
                    if fname == "player_id":
                        continue

                    setattr(pd, fname, getattr(new_p, fname))

                players_diff[pid] = pd

            else:
                pd = TexasHoldemPlayerDiff()

                for fname in TexasHoldemPlayer.model_fields:
                    if fname == "player_id":
                        continue

                    ov = getattr(old_p, fname)

                    nv = getattr(new_p, fname)

                    if serialize(ov) != serialize(nv):
                        setattr(pd, fname, nv)

                if pd.model_dump(exclude_none=True):
                    players_diff[pid] = pd

        if players_diff:
            kwargs["players"] = players_diff

        # Generic diff for all other pydantic-declared fields

        for field_name in TexasHoldemState.model_fields:
            if field_name in {"players"}:  # handled above
                continue

            ov = getattr(old, field_name)

            nv = getattr(new, field_name)

            if serialize(ov) != serialize(nv):
                kwargs[field_name] = nv

        return TexasHoldemStateDiff(**kwargs)


class TexasHoldemPlayerDiff(BaseModel):
    """Partial diff for a single `TexasHoldemPlayer`.


    Only fields that changed should be populated. All others remain None (unchanged).

    The player is identified by the key in `TexasHoldemStateDiff.players`.

    """

    chips: int | None = None

    position: int | None = None

    status: PlayerStatus | None = None

    hole_cards: list[Card] | None = None

    current_bet: int | None = None

    total_bet: int | None = None

    previous_action: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class TexasHoldemStateDiff(BaseModel):
    """Partial diff for `TexasHoldemState`.


    Only include fields that changed compared to previous state.

    - `players`: map of PlayerId -> `TexasHoldemPlayerDiff` for players that changed.

    - list fields like `community_cards`, `deck`, `winners`, `side_pots` should be the new full value if they changed at all.

    """

    game_id: GameId | None = None

    is_finished: bool | None = None

    current_player_id: PlayerId | None = None

    turn: int | None = None

    players: dict[PlayerId, TexasHoldemPlayerDiff] | None = None

    community_cards: list[Card] | None = None

    pot: int | None = None

    side_pots: list[Any] | None = None

    current_bet: int | None = None

    betting_round: BettingRound | None = None

    dealer_position: int | None = None

    small_blind_position: int | None = None

    big_blind_position: int | None = None

    action_position: int | None = None

    last_raise_amount: int | None = None

    last_raise_position: int | None = None

    deck: list[Card] | None = None

    winners: list[PlayerId] | None = None

    winning_hands: dict[PlayerId, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


# Rebuild models to ensure all forward references are resolved
TexasHoldemPlayerDiff.model_rebuild()
TexasHoldemStateDiff.model_rebuild()
