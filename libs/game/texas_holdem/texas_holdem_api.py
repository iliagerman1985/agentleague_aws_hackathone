from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum, StrEnum
from typing import Annotated, Any, Literal

from game_api import (
    BaseAgentDecision,
    BaseGameConfig,
    BaseGameEvent,
    BaseGameState,
    BaseGameStateView,
    BasePlayerMoveData,
    BasePlayerPossibleMoves,
    BasePlayerViewEvent,
    ChatMessageMixin,
    GameType,
    ReasoningEventMixin,
)
from pydantic import Field, field_validator, model_serializer, model_validator
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from common.ids import AgentVersionId, GameId, PlayerId
from common.types import AgentReasoning
from common.utils.json_model import JsonModel


class SidePot(JsonModel):
    """Represents a side pot in poker."""

    amount: int = Field(..., description="Amount in the side pot", ge=0)
    eligible_players: list[PlayerId] = Field(..., description="Player IDs eligible for this side pot")

    @field_validator("eligible_players")
    @classmethod
    def validate_eligible_players(cls, v: list[PlayerId]) -> list[PlayerId]:
        """Validate eligible players list."""
        if len(v) < 1:
            raise ValueError("Side pot must have at least one eligible player")
        return v


class TexasHoldemAction(StrEnum):
    """Possible Texas Hold'em actions."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


class PlayerStatus(StrEnum):
    """Player status in a poker game."""

    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all_in"
    OUT = "out"


class BettingRound(IntEnum):
    """Betting rounds in Texas Hold'em."""

    PREFLOP = 1
    FLOP = 2
    TURN = 3
    RIVER = 4
    SHOWDOWN = 5


class CardRank(StrEnum):
    """Card ranks as string enums for readability while supporting numeric mapping."""

    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"

    def as_int(self) -> int:
        return _RANK_TO_INT[self]

    @staticmethod
    def of(rank: int | str) -> CardRank:
        if isinstance(rank, int):
            # Convert integer ranks to string representation
            if rank == 11:
                return CardRank.JACK
            elif rank == 12:
                return CardRank.QUEEN
            elif rank == 13:
                return CardRank.KING
            elif rank == 14:
                return CardRank.ACE
            else:
                return CardRank(str(rank))
        return CardRank(rank)


_RANK_TO_INT: dict[CardRank, int] = {
    CardRank.TWO: 2,
    CardRank.THREE: 3,
    CardRank.FOUR: 4,
    CardRank.FIVE: 5,
    CardRank.SIX: 6,
    CardRank.SEVEN: 7,
    CardRank.EIGHT: 8,
    CardRank.NINE: 9,
    CardRank.TEN: 10,
    CardRank.JACK: 11,
    CardRank.QUEEN: 12,
    CardRank.KING: 13,
    CardRank.ACE: 14,
}


class CardSuit(StrEnum):
    """Card suits as string enums."""

    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    def as_symbol(self) -> str:
        return _SUITE_TO_SYMBOL[self]


_SUITE_TO_SYMBOL: dict[CardSuit, str] = {
    CardSuit.HEARTS: "♥",
    CardSuit.DIAMONDS: "♦",
    CardSuit.CLUBS: "♣",
    CardSuit.SPADES: "♠",
}


class HandRank(IntEnum):
    """Poker hand rankings from lowest to highest."""

    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


class Card(JsonModel):
    """Represents a playing card."""

    rank: CardRank = Field(..., description="Card rank (2-10, J, Q, K, A)")
    suit: CardSuit = Field(..., description="Card suit (hearts, diamonds, clubs, spades)")

    @model_serializer
    def serialize_model(self) -> str:
        """Serialize card to compact string format for JSON."""
        return self.to_compact_string()

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> dict[str, Any]:
        """Validate and deserialize card from compact string or dict format."""
        if isinstance(data, str):
            # Deserialize from compact string format
            card = cls.from_compact_string(data)
            return {"rank": card.rank, "suit": card.suit}
        elif isinstance(data, dict):
            return data
        else:
            raise ValueError(f"Invalid card data type: {type(data)}")

    @staticmethod
    def of(card_str_or_rank: str | CardRank | int, suit: CardSuit | str | None = None) -> Card:
        """Create a Card from either a single string (e.g., 'Ah', 'Kd', '10c') or rank and suit.

        Args:
            card_str_or_rank: Either a card string like 'Ah' or a rank value
            suit: Suit value (required if first arg is rank, ignored if first arg is card string)

        Returns:
            Card instance
        """
        if isinstance(card_str_or_rank, str) and suit is None:
            # Single string format like 'Ah', 'Kd', '10c'
            card_str = card_str_or_rank.strip()
            if len(card_str) < 2:
                raise ValueError(f"Invalid card string: {card_str}")

            # Last character is suit
            suit_char = card_str[-1].lower()
            rank_str = card_str[:-1]

            # Map suit characters to CardSuit
            suit_mapping = {
                "h": CardSuit.HEARTS,
                "d": CardSuit.DIAMONDS,
                "c": CardSuit.CLUBS,
                "s": CardSuit.SPADES,
            }

            if suit_char not in suit_mapping:
                raise ValueError(f"Invalid suit character: {suit_char}")

            return Card(rank=CardRank.of(rank_str), suit=suit_mapping[suit_char])
        else:
            # Two-parameter format (backward compatibility)
            if suit is None:
                raise ValueError("Suit is required when first argument is not a card string")
            return Card(rank=CardRank.of(card_str_or_rank), suit=CardSuit(suit))

    # @field_validator("rank", mode="before")
    # @classmethod
    # def coerce_rank(cls, v: object) -> CardRank:
    #     """Allow constructing Card with int or str rank values by coercing to CardRank enum."""
    #     if isinstance(v, CardRank):
    #         return v
    #     if isinstance(v, int):
    #         mapping = {
    #             2: CardRank.TWO,
    #             3: CardRank.THREE,
    #             4: CardRank.FOUR,
    #             5: CardRank.FIVE,
    #             6: CardRank.SIX,
    #             7: CardRank.SEVEN,
    #             8: CardRank.EIGHT,
    #             9: CardRank.NINE,
    #             10: CardRank.TEN,
    #             11: CardRank.JACK,
    #             12: CardRank.QUEEN,
    #             13: CardRank.KING,
    #             14: CardRank.ACE,
    #         }
    #         if v in mapping:
    #             return mapping[v]
    #         raise ValueError(f"Invalid rank: {v}")
    #     if isinstance(v, str):
    #         s = v.upper()
    #         mapping = {
    #             "2": CardRank.TWO,
    #             "3": CardRank.THREE,
    #             "4": CardRank.FOUR,
    #             "5": CardRank.FIVE,
    #             "6": CardRank.SIX,
    #             "7": CardRank.SEVEN,
    #             "8": CardRank.EIGHT,
    #             "9": CardRank.NINE,
    #             "10": CardRank.TEN,
    #             "J": CardRank.JACK,
    #             "Q": CardRank.QUEEN,
    #             "K": CardRank.KING,
    #             "A": CardRank.ACE,
    #         }
    #         if s in mapping:
    #             return mapping[s]
    #         raise ValueError(f"Invalid rank: {v}")
    #     raise ValueError(f"Invalid rank type: {type(v)}")

    # @field_validator("suit", mode="before")
    # @classmethod
    # def coerce_suit(cls, v: object) -> CardSuit:
    #     """Allow constructing Card with str suit values by coercing to CardSuit enum."""
    #     if isinstance(v, CardSuit):
    #         return v
    #     if isinstance(v, str):
    #         mapping = {
    #             "hearts": CardSuit.HEARTS,
    #             "diamonds": CardSuit.DIAMONDS,
    #             "clubs": CardSuit.CLUBS,
    #             "spades": CardSuit.SPADES,
    #         }
    #         s = v.lower()
    #         if s in mapping:
    #             return mapping[s]
    #         raise ValueError(f"Invalid suit: {v}")
    #     raise ValueError(f"Invalid suit type: {type(v)}")

    def __str__(self) -> str:
        """String representation of the card."""
        return f"{self.rank.value}{self.suit.as_symbol()}"

    def __hash__(self) -> int:
        """Make Card hashable for use in sets and as dict keys."""
        return hash((self.rank, self.suit))

    def __eq__(self, other: object) -> bool:
        """Check equality between cards."""
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def to_compact_string(self) -> str:
        """Convert card to compact string format like 'Qs', 'Ah', '10h'."""
        suit_mapping = {
            CardSuit.HEARTS: "h",
            CardSuit.DIAMONDS: "d",
            CardSuit.CLUBS: "c",
            CardSuit.SPADES: "s",
        }
        return f"{self.rank.value}{suit_mapping[self.suit]}"

    @classmethod
    def from_compact_string(cls, compact_str: str) -> "Card":
        """Create card from compact string format like 'Qs', 'Ah', '10h'."""
        return cls.of(compact_str)


class HandResult(JsonModel):
    """Result of evaluating a poker hand."""

    rank: HandRank = Field(..., description="Hand rank")
    high_cards: list[Card] = Field(..., description="High card ranks for tie-breaking")
    description: str = Field(..., description="Human-readable description")

    @property
    def high_card(self) -> Card | None:
        """Get the highest card rank."""
        return self.high_cards[0] if self.high_cards else None

    @property
    def kicker(self) -> Card | None:
        """Get the kicker rank (second highest relevant card)."""
        return self.high_cards[1] if len(self.high_cards) > 1 else None

    def __lt__(self, other: HandResult) -> bool:
        """Compare hands for ranking."""
        if self.rank != other.rank:
            return self.rank < other.rank
        return self.high_cards < other.high_cards


class TexasHoldemConfig(BaseGameConfig):
    """Configuration for Texas Hold'em games."""

    env: GameType = GameType.TEXAS_HOLDEM
    small_blind: int = Field(..., description="Small blind amount", gt=0)
    big_blind: int = Field(..., description="Big blind amount", gt=0)
    starting_chips: int = Field(..., description="Starting chips per player", gt=0)
    starting_chips_override_for_test: dict[AgentVersionId, int] | None = Field(default=None, description="Starting chips per player for testing")
    default_dealer_position: int = Field(default=0, description="Default dealer position")
    min_raise: int | None = Field(default=None, description="Minimum raise amount")
    max_raise: int | None = Field(default=None, description="Maximum raise amount")

    @model_validator(mode="after")
    def validate_config(self) -> TexasHoldemConfig:
        """Validate configuration after initialization."""
        if self.big_blind <= self.small_blind:
            raise THErrors.VALIDATION_ERROR.create(
                message="Big blind must be greater than small blind",
                details={"big_blind": self.big_blind, "small_blind": self.small_blind},
            )
        if self.min_raise is not None and self.min_raise < self.big_blind:
            raise THErrors.VALIDATION_ERROR.create(
                message="Minimum raise must be at least the big blind",
                details={"min_raise": self.min_raise, "big_blind": self.big_blind},
            )
        if self.max_raise is not None and self.min_raise is not None and self.max_raise < self.min_raise:
            raise THErrors.VALIDATION_ERROR.create(
                message="Maximum raise must be at least the minimum raise",
                details={"max_raise": self.max_raise, "min_raise": self.min_raise},
            )
        return self


class TexasHoldemState(BaseGameState):
    env: GameType = GameType.TEXAS_HOLDEM
    betting_round: BettingRound = Field(default=BettingRound.PREFLOP, description="Current betting round")
    deck: list[Card] = Field(default_factory=list, description="Remaining cards in deck")
    community_cards: list[Card] = Field(default_factory=list, description="Community cards")
    players: list[TexasHoldemPlayer] = Field(..., description="Players in the game")
    pot: int = Field(default=0, description="Current pot amount", ge=0)
    side_pots: list[SidePot] = Field(default_factory=list, description="Side pots for all-in scenarios")
    current_bet: int = Field(default=0, description="Current bet amount to call", ge=0)
    dealer_position: int = Field(default=0, description="Dealer position", ge=0)
    small_blind_position: int = Field(default=0, description="Small blind position", ge=0)
    big_blind_position: int = Field(default=0, description="Big blind position", ge=0)
    action_position: int = Field(default=0, description="Position of player to act", ge=0)
    last_raise_amount: int = Field(default=0, description="Amount of last raise", ge=0)
    last_raise_position: int | None = Field(default=None, description="Position of last raiser")
    acted_positions: list[int] = Field(default_factory=list, description="Positions of players who have acted this round")
    winners: list[PlayerId] = Field(default_factory=list, description="Winner player IDs if game is over")
    winning_hands: dict[PlayerId, HandResult] = Field(default_factory=dict, description="Winning hands by player ID")

    def get_player_by_id(self, player_id: PlayerId) -> TexasHoldemPlayer:
        """Get player by ID."""
        for player in self.players:
            if player.player_id == player_id:
                return player
        raise THErrors.INVALID_GAME_STATE.create(message=f"Player ID {player_id} not found", details={"player_id": player_id})


class TexasHoldemPlayer(JsonModel):
    """Represents a player in a Texas Hold'em game."""

    player_id: PlayerId = Field(..., description="Unique player identifier")
    chips: int = Field(..., description="Number of chips the player has", ge=0)
    status: PlayerStatus = Field(default=PlayerStatus.ACTIVE, description="Current player status")
    current_bet: int = Field(default=0, description="Amount bet in current round", ge=0)
    total_bet: int = Field(default=0, description="Total amount bet in the hand", ge=0)
    previous_action: PlayerActionEvent | None = Field(default=None, description="Previous action taken by the player")
    position: int = Field(..., description="Player's position in the game")
    hole_cards: list[Card] = Field(default_factory=list, description="Player's hole cards")

    def to_other_player_view(self) -> TexasHoldemOtherPlayerView:
        """Convert to other player view (without hole cards)."""
        return TexasHoldemOtherPlayerView(
            player_id=self.player_id,
            chips=self.chips,
            status=self.status,
            current_bet=self.current_bet,
            total_bet=self.total_bet,
            previous_action=self.previous_action,
            position=self.position,
        )


class TexasHoldemStateView(BaseGameStateView):
    events: Sequence[TexasHoldemPlayerViewEvent] = Field(
        default_factory=list, description="Events relevant to the player"
    )  # Must remain here as it provides the concrete type of the events.
    betting_round: BettingRound = Field(default=BettingRound.PREFLOP, description="Current betting round")
    community_cards: list[Card] = Field(default_factory=list, description="Community cards")
    me: TexasHoldemPlayer = Field(..., description="Current player's state")
    already_played_players: list[TexasHoldemOtherPlayerView] = Field(..., description="Player who already played in this round")
    should_play_players: list[TexasHoldemOtherPlayerView] = Field(..., description="Players still to play in this round")
    pot: int = Field(default=0, description="Current pot amount", ge=0)
    side_pots: list[SidePot] = Field(default_factory=list, description="Side pots for all-in scenarios")
    current_bet: int = Field(default=0, description="Current bet amount to call", ge=0)
    dealer_position: int = Field(default=0, description="Dealer position", ge=0)
    small_blind_position: int = Field(default=0, description="Small blind position", ge=0)
    big_blind_position: int = Field(default=0, description="Big blind position", ge=0)
    last_raise_amount: int = Field(default=0, description="Amount of last raise", ge=0)
    last_raise_position: int | None = Field(default=None, description="Position of last raiser")
    winners: list[PlayerId] | None = Field(default=None, description="Winner player IDs if game is over")
    winning_hands: dict[PlayerId, HandResult] | None = Field(default=None, description="Winning hands by player ID")


class TexasHoldemOtherPlayerView(JsonModel):
    """Represents a player in a Texas Hold'em game."""

    player_id: PlayerId = Field(..., description="Unique player identifier")
    chips: int = Field(..., description="Number of chips the player has", ge=0)
    status: PlayerStatus = Field(default=PlayerStatus.ACTIVE, description="Current player status")
    current_bet: int = Field(default=0, description="Amount bet in current round", ge=0)
    total_bet: int = Field(default=0, description="Total amount bet in the hand", ge=0)
    previous_action: PlayerActionEvent | None = Field(default=None, description="Previous action taken by the player")
    position: int = Field(..., description="Player's position in the game")


class TexasHoldemMoveData(BasePlayerMoveData):
    """Player move in Texas Hold'em."""

    action: TexasHoldemAction = Field(..., description="Action to take")
    amount: int | None = Field(default=None, description="Bet/raise amount, should only be non-null for raise", ge=0)

    @model_validator(mode="after")
    def validate_move(self) -> TexasHoldemMoveData:
        """Validate move."""
        if self.action == TexasHoldemAction.RAISE and self.amount is None:
            raise THErrors.INVALID_ACTION.create(message="Raise action requires an amount", details={"action": self.action.value})
        if self.action in (TexasHoldemAction.FOLD, TexasHoldemAction.CHECK, TexasHoldemAction.CALL, TexasHoldemAction.ALL_IN) and self.amount is not None:
            raise THErrors.INVALID_ACTION.create(message=f"Action {self.action} should not have an amount", details={"action": self.action.value})

        return self


class TexasHoldemPossibleMove(JsonModel):
    """Possible move for Texas Hold'em."""

    action: TexasHoldemAction = Field(..., description="Action to take")
    amount: int | None = Field(default=None, description="Bet/raise amount", ge=0)
    min_raise_amount: int | None = Field(default=None, description="Minimum amount to raise to if raising", ge=0)
    max_raise_amount: int | None = Field(default=None, description="Maximum amount to raise to if raising", ge=0)


class TexasHoldemPossibleMoves(BasePlayerPossibleMoves):
    """Possible moves for Texas Hold'em."""

    possible_moves: list[TexasHoldemPossibleMove] = Field(..., description="List of possible moves")


class TexasHoldemEventType(StrEnum):
    """Event types for Texas Hold'em events."""

    GAME_INITIALIZED = "game_initialized"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    HAND_STARTED = "hand_started"
    HOLE_CARDS_DEALT = "hole_cards_dealt"
    PLAYER_ACTION = "player_action"
    POT_UPDATE = "pot_update"
    BETTING_ROUND_ADVANCED = "betting_round_advanced"
    COMMUNITY_CARDS_DEALT = "community_cards_dealt"
    SIDE_POTS_CREATED = "side_pots_created"
    HAND_EVALUATED = "hand_evaluated"
    WINNERS_ANNOUNCED = "winners_announced"
    CHIPS_DISTRIBUTED = "chips_distributed"
    PLAYER_STATUS_CHANGED = "player_status_changed"
    GAME_FINISHED = "game_finished"
    AGENT_REASONING = "agent_reasoning"
    CHAT_MESSAGE = "chat_message"


class PlayerStatusChangeReason(StrEnum):
    """Reasons for player status changes."""

    FOLDED_ACTION = "folded_action"
    ALL_IN_ACTION = "all_in_action"
    INSUFFICIENT_CHIPS = "insufficient_chips"
    GAME_ENDED = "game_ended"
    HAND_ENDED = "hand_ended"
    FORCED_ALL_IN = "forced_all_in"


class BaseTexasHoldemEvent[T: TexasHoldemEventType](BaseGameEvent):
    """Base class for all Texas Hold'em events."""

    type: T = Field(..., description="Type of event")


class GameInitializedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.GAME_INITIALIZED]):
    """Event emitted when a new game is initialized."""

    type: Literal[TexasHoldemEventType.GAME_INITIALIZED] = TexasHoldemEventType.GAME_INITIALIZED
    game_id: GameId = Field(..., description="Game ID")


class PlayerJoinedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.PLAYER_JOINED]):
    """Event emitted when a player joins the game."""

    type: Literal[TexasHoldemEventType.PLAYER_JOINED] = TexasHoldemEventType.PLAYER_JOINED
    player_id: PlayerId = Field(..., description="Player ID")
    agent_version_id: AgentVersionId = Field(..., description="Agent version ID")
    name: str = Field(..., description="Player name")


class PlayerLeftEvent(BaseTexasHoldemEvent[TexasHoldemEventType.PLAYER_LEFT]):
    """Event emitted when a player leaves the game."""

    type: Literal[TexasHoldemEventType.PLAYER_LEFT] = TexasHoldemEventType.PLAYER_LEFT
    player_id: PlayerId = Field(..., description="ID of player who left")
    reason: str = Field(default="disconnect", description="Reason for leaving")
    turn: int = Field(..., description="Round when player left")


class PlayerStatusChangedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.PLAYER_STATUS_CHANGED]):
    """Event emitted when a player's status changes (e.g., OUT due to insufficient chips)."""

    type: Literal[TexasHoldemEventType.PLAYER_STATUS_CHANGED] = TexasHoldemEventType.PLAYER_STATUS_CHANGED
    turn: int = Field(..., description="Round number")
    player_id: PlayerId = Field(..., description="Player ID")
    from_status: PlayerStatus = Field(..., description="Previous status")
    to_status: PlayerStatus = Field(..., description="New status")
    reason: PlayerStatusChangeReason = Field(..., description="Reason for status change")


class HandStartedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.HAND_STARTED]):
    """Event emitted when a new hand starts."""

    type: Literal[TexasHoldemEventType.HAND_STARTED] = TexasHoldemEventType.HAND_STARTED
    dealer_position: int = Field(..., description="Dealer position for this hand")
    small_blind_position: int = Field(..., description="Small blind position")
    big_blind_position: int = Field(..., description="Big blind position")
    small_blind_amount: int = Field(..., description="Small blind amount")
    big_blind_amount: int = Field(..., description="Big blind amount")
    small_blind_forced_all_in: bool | None = Field(default=None, description="Whether small blind player was forced all-in (only present when true)")
    big_blind_forced_all_in: bool | None = Field(default=None, description="Whether big blind player was forced all-in (only present when true)")


class HoleCardsDealtEvent(BaseTexasHoldemEvent[TexasHoldemEventType.HOLE_CARDS_DEALT]):
    """Event emitted when hole cards are dealt to players."""

    type: Literal[TexasHoldemEventType.HOLE_CARDS_DEALT] = TexasHoldemEventType.HOLE_CARDS_DEALT
    player_cards: dict[PlayerId, list[Card]] = Field(..., description="Hole cards dealt to each player")


class PlayerActionEvent(BaseTexasHoldemEvent[TexasHoldemEventType.PLAYER_ACTION]):
    """Event emitted when a player takes an action."""

    type: Literal[TexasHoldemEventType.PLAYER_ACTION] = TexasHoldemEventType.PLAYER_ACTION
    player_id: PlayerId = Field(..., description="Player taking the action")
    action: TexasHoldemAction = Field(..., description="Action taken")
    amount: int | None = Field(default=None, description="Amount for raise actions")
    player_chips_before: int = Field(..., description="Player's chips before action")
    player_chips_after: int = Field(..., description="Player's chips after action")
    player_bet_before: int = Field(..., description="Player's current bet before action")
    player_bet_after: int = Field(..., description="Player's current bet after action")
    forced_all_in: bool | None = Field(default=None, description="Whether action resulted in forced all-in (only present when true)")
    thinking_time_ms: int | None = Field(default=None, description="Time taken to make decision in milliseconds")
    status_before: PlayerStatus = Field(..., description="Player's status before action")
    status_after: PlayerStatus = Field(..., description="Player's status after action")
    status_change_reason: PlayerStatusChangeReason | None = Field(default=None, description="Reason for status change if any")


class PotUpdateEvent(BaseTexasHoldemEvent[TexasHoldemEventType.POT_UPDATE]):
    """Event emitted when the pot is updated."""

    type: Literal[TexasHoldemEventType.POT_UPDATE] = TexasHoldemEventType.POT_UPDATE
    pot_before: int = Field(..., description="Pot amount before update")
    pot_after: int = Field(..., description="Pot amount after update")
    amount_added: int = Field(..., description="Amount added to pot")
    current_bet_before: int = Field(..., description="Current bet before update")
    current_bet_after: int = Field(..., description="Current bet after update")


class BettingRoundAdvancedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.BETTING_ROUND_ADVANCED]):
    """Event emitted when betting round advances."""

    type: Literal[TexasHoldemEventType.BETTING_ROUND_ADVANCED] = TexasHoldemEventType.BETTING_ROUND_ADVANCED
    from_round: BettingRound = Field(..., description="Previous betting round")
    to_round: BettingRound = Field(..., description="New betting round")
    next_player_id: PlayerId | None = Field(default=None, description="Next player to act (if any)")


class CommunityCardsDealtEvent(BaseTexasHoldemEvent[TexasHoldemEventType.COMMUNITY_CARDS_DEALT]):
    """Event emitted when community cards are dealt."""

    type: Literal[TexasHoldemEventType.COMMUNITY_CARDS_DEALT] = TexasHoldemEventType.COMMUNITY_CARDS_DEALT
    cards: list[Card] = Field(..., description="Cards dealt")
    deal_type: Literal["flop", "turn", "river", "runout"] = Field(..., description="Type of deal")
    total_community_cards: int = Field(..., description="Total community cards after deal")


class SidePotsCreatedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.SIDE_POTS_CREATED]):
    """Event emitted when side pots are created."""

    type: Literal[TexasHoldemEventType.SIDE_POTS_CREATED] = TexasHoldemEventType.SIDE_POTS_CREATED
    side_pots: list[SidePot] = Field(..., description="Side pots created")
    main_pot_amount: int = Field(..., description="Remaining main pot amount")


class HandEvaluatedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.HAND_EVALUATED]):
    """Event emitted when hands are evaluated at showdown."""

    type: Literal[TexasHoldemEventType.HAND_EVALUATED] = TexasHoldemEventType.HAND_EVALUATED
    player_id: PlayerId = Field(..., description="Player whose hand was evaluated")
    hand_result: HandResult = Field(..., description="Hand evaluation result")
    final_hand: list[Card] = Field(..., description="Best 5-card hand")


class WinnersAnnouncedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.WINNERS_ANNOUNCED]):
    """Event emitted when winners are announced."""

    type: Literal[TexasHoldemEventType.WINNERS_ANNOUNCED] = TexasHoldemEventType.WINNERS_ANNOUNCED
    winners: list[PlayerId] = Field(..., description="Winner player IDs")
    winning_hands: dict[PlayerId, HandResult] = Field(..., description="Winning hands by player")
    uncontested: bool | None = Field(default=None, description="Whether win was uncontested (only present when true)")


class ChipsDistributedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.CHIPS_DISTRIBUTED]):
    """Event emitted when chips are distributed to winners."""

    type: Literal[TexasHoldemEventType.CHIPS_DISTRIBUTED] = TexasHoldemEventType.CHIPS_DISTRIBUTED
    distributions: list[dict[str, PlayerId | int | str]] = Field(..., description="Chip distributions")
    # Each distribution dict has: player_id, amount, source ("main_pot" or "side_pot_N")


class GameFinishedEvent(BaseTexasHoldemEvent[TexasHoldemEventType.GAME_FINISHED]):
    """Event emitted when the game finishes."""

    type: Literal[TexasHoldemEventType.GAME_FINISHED] = TexasHoldemEventType.GAME_FINISHED
    final_chip_counts: dict[PlayerId, int] = Field(..., description="Final chip counts for all players")


class AgentReasoningEvent(ReasoningEventMixin, BaseTexasHoldemEvent[TexasHoldemEventType.AGENT_REASONING]):
    """Event emitted when an agent provides reasoning for their move."""

    type: Literal[TexasHoldemEventType.AGENT_REASONING] = TexasHoldemEventType.AGENT_REASONING


class ChatMessageEvent(ChatMessageMixin, BaseTexasHoldemEvent[TexasHoldemEventType.CHAT_MESSAGE]):
    """Event emitted when an agent sends a chat message."""

    type: Literal[TexasHoldemEventType.CHAT_MESSAGE] = TexasHoldemEventType.CHAT_MESSAGE


class TexasHoldemAgentDecision(BaseAgentDecision[TexasHoldemMoveData]):
    pass


type TexasHoldemEvent = Annotated[
    GameInitializedEvent
    | PlayerJoinedEvent
    | PlayerLeftEvent
    | HandStartedEvent
    | HoleCardsDealtEvent
    | PlayerActionEvent
    | PotUpdateEvent
    | BettingRoundAdvancedEvent
    | CommunityCardsDealtEvent
    | SidePotsCreatedEvent
    | HandEvaluatedEvent
    | WinnersAnnouncedEvent
    | ChipsDistributedEvent
    | PlayerStatusChangedEvent
    | GameFinishedEvent
    | AgentReasoningEvent
    | ChatMessageEvent,
    Field(discriminator="type"),
]


class PlayerJoinedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of player joined event."""

    event: Literal["Player Joined"] = "Player Joined"
    player_id: PlayerId = Field(..., description="Player ID")
    name: str = Field(..., description="Player name")


class PlayerLeftPlayerViewEvent(BasePlayerViewEvent):
    """Player view of player left event."""

    event: Literal["Player Left"] = "Player Left"
    player_id: PlayerId = Field(..., description="ID of player who left")
    reason: str = Field(default="disconnect", description="Reason for leaving")


class PlayerStatusChangedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of player status changed event."""

    event: Literal["Player Status Changed"] = "Player Status Changed"
    player_id: PlayerId = Field(..., description="Player ID")
    from_status: PlayerStatus = Field(..., description="Previous status")
    to_status: PlayerStatus = Field(..., description="New status")
    reason: PlayerStatusChangeReason = Field(..., description="Reason for status change")


class HandStartedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of hand started event."""

    event: Literal["Hand Started"] = "Hand Started"
    dealer_position: int = Field(..., description="Dealer position for this hand")
    small_blind_position: int = Field(..., description="Small blind position")
    big_blind_position: int = Field(..., description="Big blind position")
    small_blind_amount: int = Field(..., description="Small blind amount")
    big_blind_amount: int = Field(..., description="Big blind amount")
    small_blind_forced_all_in: bool | None = Field(default=None, description="Whether small blind player was forced all-in")
    big_blind_forced_all_in: bool | None = Field(default=None, description="Whether big blind player was forced all-in")


class HoleCardsDealtPlayerViewEvent(BasePlayerViewEvent):
    """Player view of hole cards dealt event - only shows viewer's cards."""

    event: Literal["Hole Cards Dealt"] = "Hole Cards Dealt"
    my_cards: list[Card] = Field(..., description="Hole cards dealt to the viewing player")


class PlayerActionPlayerViewEvent(BasePlayerViewEvent):
    """Player view of player action event."""

    event: Literal["Player Action"] = "Player Action"
    player_id: PlayerId = Field(..., description="Player taking the action")
    action: TexasHoldemAction = Field(..., description="Action taken")
    amount: int | None = Field(default=None, description="Amount for raise actions")
    player_chips_before: int = Field(..., description="Player's chips before action")
    player_chips_after: int = Field(..., description="Player's chips after action")
    player_bet_before: int = Field(..., description="Player's current bet before action")
    player_bet_after: int = Field(..., description="Player's current bet after action")
    forced_all_in: bool | None = Field(default=None, description="Whether action resulted in forced all-in")
    thinking_time_ms: int | None = Field(default=None, description="Time taken to make decision in milliseconds")
    status_before: PlayerStatus = Field(..., description="Player's status before action")
    status_after: PlayerStatus = Field(..., description="Player's status after action")
    status_change_reason: PlayerStatusChangeReason | None = Field(default=None, description="Reason for status change if any")


class PotUpdatePlayerViewEvent(BasePlayerViewEvent):
    """Player view of pot update event."""

    event: Literal["Pot Update"] = "Pot Update"
    pot_before: int = Field(..., description="Pot amount before update")
    pot_after: int = Field(..., description="Pot amount after update")
    amount_added: int = Field(..., description="Amount added to pot")
    current_bet_before: int = Field(..., description="Current bet before update")
    current_bet_after: int = Field(..., description="Current bet after update")


class BettingRoundAdvancedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of betting round advanced event."""

    event: Literal["Betting Round Advanced"] = "Betting Round Advanced"
    from_round: BettingRound = Field(..., description="Previous betting round")
    to_round: BettingRound = Field(..., description="New betting round")
    next_player_id: PlayerId | None = Field(default=None, description="Next player to act (if any)")


class CommunityCardsDealtPlayerViewEvent(BasePlayerViewEvent):
    """Player view of community cards dealt event."""

    event: Literal["Community Cards Dealt"] = "Community Cards Dealt"
    cards: list[Card] = Field(..., description="Cards dealt")
    deal_type: Literal["flop", "turn", "river", "runout"] = Field(..., description="Type of deal")
    total_community_cards: int = Field(..., description="Total community cards after deal")


class SidePotsCreatedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of side pots created event."""

    event: Literal["Side Pots Created"] = "Side Pots Created"
    side_pots: list[SidePot] = Field(..., description="Side pots created")
    main_pot_amount: int = Field(..., description="Remaining main pot amount")


class HandEvaluatedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of hand evaluated event."""

    event: Literal["Hand Evaluated"] = "Hand Evaluated"
    player_id: PlayerId = Field(..., description="Player whose hand was evaluated")
    hand_result: HandResult = Field(..., description="Hand evaluation result")
    final_hand: list[Card] = Field(..., description="Best 5-card hand")


class WinnersAnnouncedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of winners announced event."""

    event: Literal["Winners Announced"] = "Winners Announced"
    winners: list[PlayerId] = Field(..., description="Winner player IDs")
    winning_hands: dict[PlayerId, HandResult] = Field(..., description="Winning hands by player")
    uncontested: bool | None = Field(default=None, description="Whether win was uncontested (only present when true)")


class ChipsDistributedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of chips distributed event."""

    event: Literal["Chips Distributed"] = "Chips Distributed"
    distributions: list[dict[str, PlayerId | int | str]] = Field(..., description="Chip distributions")


class GameFinishedPlayerViewEvent(BasePlayerViewEvent):
    """Player view of game finished event."""

    event: Literal["Game Finished"] = "Game Finished"
    final_chip_counts: dict[PlayerId, int] = Field(..., description="Final chip counts for all players")


class AgentReasoningPlayerViewEvent(BasePlayerViewEvent):
    """Player view of agent reasoning event - only shown to the reasoning player."""

    event: Literal["Agent Reasoning"] = "Agent Reasoning"
    player_id: PlayerId = Field(..., description="Player ID of the agent")
    reasoning: AgentReasoning = Field(..., description="Agent's reasoning for the action/move")


class ChatMessagePlayerViewEvent(ChatMessageMixin, BasePlayerViewEvent):
    """Player view of chat message event."""

    event: Literal["Chat Message"] = "Chat Message"


# Player View Event Union Type
type TexasHoldemPlayerViewEvent = Annotated[
    PlayerJoinedPlayerViewEvent
    | PlayerLeftPlayerViewEvent
    | HandStartedPlayerViewEvent
    | HoleCardsDealtPlayerViewEvent
    | PlayerActionPlayerViewEvent
    | PotUpdatePlayerViewEvent
    | BettingRoundAdvancedPlayerViewEvent
    | CommunityCardsDealtPlayerViewEvent
    | SidePotsCreatedPlayerViewEvent
    | WinnersAnnouncedPlayerViewEvent
    | ChipsDistributedPlayerViewEvent
    | PlayerStatusChangedPlayerViewEvent
    | GameFinishedPlayerViewEvent
    | AgentReasoningPlayerViewEvent
    | ChatMessagePlayerViewEvent,
    Field(discriminator="event"),
]
