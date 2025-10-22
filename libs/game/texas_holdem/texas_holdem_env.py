"""Texas Hold'em implementation for the game engine framework."""

from __future__ import annotations

import random
from itertools import combinations
from typing import Any, override

from game_api import (
    NO_PLAYER_ID,
    BaseGameEvent,
    EventCollector,
    FinishDecision,
    GameAnalysisHandler,
    GameEnv,
    GameEnvTypes,
    GameId,
    GameResult,
    GameType,
    PlayerMove,
)
from texas_holdem import (
    BettingRound,
    Card,
    CardRank,
    CardSuit,
    HandRank,
    HandResult,
    PlayerStatus,
    TexasHoldemAction,
    TexasHoldemConfig,
    TexasHoldemMoveData,
    TexasHoldemPlayer,
    TexasHoldemState,
)
from texas_holdem.texas_holdem_api import (
    AgentReasoningEvent,
    AgentReasoningPlayerViewEvent,
    BettingRoundAdvancedEvent,
    BettingRoundAdvancedPlayerViewEvent,
    ChatMessageEvent,
    ChatMessagePlayerViewEvent,
    ChipsDistributedEvent,
    ChipsDistributedPlayerViewEvent,
    CommunityCardsDealtEvent,
    CommunityCardsDealtPlayerViewEvent,
    GameFinishedEvent,
    GameFinishedPlayerViewEvent,
    GameInitializedEvent,
    HandEvaluatedEvent,
    HandStartedEvent,
    HandStartedPlayerViewEvent,
    HoleCardsDealtEvent,
    HoleCardsDealtPlayerViewEvent,
    PlayerActionEvent,
    PlayerActionPlayerViewEvent,
    PlayerJoinedEvent,
    PlayerJoinedPlayerViewEvent,
    PlayerLeftEvent,
    PlayerLeftPlayerViewEvent,
    PlayerStatusChangedEvent,
    PlayerStatusChangedPlayerViewEvent,
    PlayerStatusChangeReason,
    PotUpdateEvent,
    PotUpdatePlayerViewEvent,
    SidePot,
    SidePotsCreatedEvent,
    SidePotsCreatedPlayerViewEvent,
    TexasHoldemAgentDecision,
    TexasHoldemEvent,
    TexasHoldemOtherPlayerView,
    TexasHoldemPlayerViewEvent,
    TexasHoldemPossibleMove,
    TexasHoldemPossibleMoves,
    TexasHoldemStateView,
    WinnersAnnouncedEvent,
    WinnersAnnouncedPlayerViewEvent,
)
from texas_holdem.texas_holdem_errors import TexasHoldemErrors as THErrors

from common.ids import AgentVersionId, PlayerId
from common.types import AgentReasoning, ExecutedToolCall

_DECK = [
    Card(rank=rank, suit=suit)
    for suit in [
        CardSuit.HEARTS,
        CardSuit.DIAMONDS,
        CardSuit.CLUBS,
        CardSuit.SPADES,
    ]
    for rank in [
        CardRank.TWO,
        CardRank.THREE,
        CardRank.FOUR,
        CardRank.FIVE,
        CardRank.SIX,
        CardRank.SEVEN,
        CardRank.EIGHT,
        CardRank.NINE,
        CardRank.TEN,
        CardRank.JACK,
        CardRank.QUEEN,
        CardRank.KING,
        CardRank.ACE,
    ]
]


class TexasHoldemEnv(GameEnv[TexasHoldemState, TexasHoldemStateView, TexasHoldemEvent, TexasHoldemMoveData, TexasHoldemConfig, TexasHoldemPossibleMoves]):
    """Environment for Texas Hold'em poker."""

    def __init__(self, config: TexasHoldemConfig, analysis_handler: GameAnalysisHandler) -> None:
        super().__init__(config, analysis_handler)

    @override
    @classmethod
    def create(cls, config: TexasHoldemConfig, analysis_handler: GameAnalysisHandler) -> TexasHoldemEnv:
        return TexasHoldemEnv(config, analysis_handler)

    @override
    @classmethod
    def types(
        cls,
    ) -> type[GameEnvTypes[TexasHoldemState, TexasHoldemStateView, TexasHoldemEvent, TexasHoldemMoveData, TexasHoldemConfig, TexasHoldemPossibleMoves]]:
        return TexasHoldemEnvTypes

    @override
    def new_game(self, game_id: GameId, event_collector: EventCollector[TexasHoldemEvent]) -> TexasHoldemState:
        """Initialize a new game."""

        state = TexasHoldemState(
            game_id=game_id,
            env=self.config.env,
            current_player_id=NO_PLAYER_ID,  # Set to system player initially
            turn=1,
            players=[],  # No players initially
            dealer_position=0,
        )

        # Emit basic game initialized event
        event_collector.add(GameInitializedEvent(turn=state.turn, game_id=game_id))

        return state

    @override
    def new_round(self, prev_state: TexasHoldemState, event_collector: EventCollector[TexasHoldemEvent]) -> TexasHoldemState:
        """Initialize state for a new game round. Returns new state."""
        # Find next dealer position among non-OUT players
        current_dealer_position = prev_state.dealer_position
        dealer_position = current_dealer_position
        for i in range(1, len(prev_state.players)):
            next_idx = (current_dealer_position + i) % len(prev_state.players)
            next_player = prev_state.players[next_idx]
            if next_player.status != PlayerStatus.OUT:
                dealer_position = next_idx
                break

        if dealer_position == current_dealer_position:
            raise THErrors.VALIDATION_ERROR.create(message="No active players found for new round")

        state = TexasHoldemState(
            game_id=prev_state.game_id,
            env=prev_state.env,
            turn=prev_state.turn + 1,
            # Reset player bets and cards, preserve chips and OUT status
            players=[
                TexasHoldemPlayer(
                    player_id=prev_player.player_id,
                    chips=prev_player.chips,
                    status=PlayerStatus.ACTIVE if prev_player.status != PlayerStatus.OUT else PlayerStatus.OUT,
                    position=prev_player.position,
                )
                for prev_player in prev_state.players
            ],
            current_player_id=prev_state.players[dealer_position].player_id,
            dealer_position=dealer_position,
        )

        # Initialize round-specific state
        self._init_new_round(state, event_collector)

        return state

    @override
    def join_player(
        self, state: TexasHoldemState, player_id: PlayerId, event_collector: EventCollector[TexasHoldemEvent], agent_version_id: AgentVersionId, name: str
    ) -> None:
        """Add a player to the game state."""

        # Create new player with initial chips
        new_player = TexasHoldemPlayer(
            player_id=player_id,
            chips=self.config.starting_chips,
            status=PlayerStatus.ACTIVE,
            position=len(state.players),  # Position is based on join order
        )

        # Add player to the list
        state.players.append(new_player)

        # If this is the first player, set them as current player
        if len(state.players) == 1:
            state.current_player_id = player_id
            state.action_position = 0

        # Emit PlayerJoined event
        event_collector.add(PlayerJoinedEvent(player_id=player_id, turn=state.turn, agent_version_id=agent_version_id, name=name))

    @override
    def apply_move(self, state: TexasHoldemState, move: PlayerMove[TexasHoldemMoveData], event_collector: EventCollector[TexasHoldemEvent]) -> None:
        self._validate_move(state, move)
        self._apply_move(state, move, event_collector)

        players_in_hand = [p for p in state.players if p.status in (PlayerStatus.ACTIVE, PlayerStatus.ALL_IN)]
        active_players = [p for p in players_in_hand if p.status == PlayerStatus.ACTIVE]

        # Find next player that still needs to act in the current round
        next_action_position = self._find_next_action_position(state)
        if next_action_position is not None:
            # This player still needs to act
            state.action_position = next_action_position
            state.current_player_id = state.players[next_action_position].player_id
        else:
            # No players need to act. Everyone has either called, folded, or is all-in. Advance to next round.
            self._advance_betting_round(state, event_collector, players_in_hand=players_in_hand, active_players=active_players)

        if state.betting_round == BettingRound.SHOWDOWN:
            self._finalize_game(state, event_collector, players_in_hand)

    def _validate_move(self, state: TexasHoldemState, move: PlayerMove[TexasHoldemMoveData]) -> None:
        # Check if game is over
        if state.is_finished:
            raise THErrors.GAME_OVER.create(message="Game has already ended", details={"player_id": move.player_id})

        # Check if betting is allowed in current round
        if state.betting_round == BettingRound.SHOWDOWN:
            raise THErrors.INVALID_ACTION.create(
                message="No moves allowed during showdown",
                details={"player_id": move.player_id, "betting_round": state.betting_round.value},
            )

        # Check if it's the player's turn
        player = state.players[state.action_position]
        if not player or player.player_id != move.player_id:
            raise THErrors.NOT_PLAYER_TURN.create(
                message=f"It's not {move.player_id}'s turn, current player is {player.player_id if player else None}",
                details={"player_id": move.player_id, "current_player": player.player_id if player else None},
            )

        # Check if player is active
        if player.status != PlayerStatus.ACTIVE:
            raise THErrors.INVALID_GAME_STATE.create(
                message=f"Player {move.player_id} is not active ({player.status})",
                details={"player_id": move.player_id, "player_status": player.status.value},
            )

        # Players without chips cannot make moves
        if player.chips == 0:
            raise THErrors.NO_CHIPS.create(message="Player has no chips", details={"player_id": move.player_id})

    def _apply_move(self, state: TexasHoldemState, move: PlayerMove[TexasHoldemMoveData], event_collector: EventCollector[TexasHoldemEvent]) -> None:
        player = state.players[state.action_position]

        # Capture before state for events
        chips_before = player.chips
        bet_before = player.current_bet
        status_before = player.status
        pot_before = state.pot
        current_bet_before = state.current_bet
        status_change_reason: PlayerStatusChangeReason | None = None

        match move.data.action:
            case TexasHoldemAction.FOLD:
                player.status = PlayerStatus.FOLDED
                status_change_reason = PlayerStatusChangeReason.FOLDED_ACTION

            case TexasHoldemAction.CHECK:
                # Can only check if no bet to call
                if state.current_bet > player.current_bet:
                    raise THErrors.CANNOT_CHECK.create(
                        details={"player_id": move.player_id, "current_bet": state.current_bet, "player_bet": player.current_bet},
                    )

                # No other state to change

            case TexasHoldemAction.CALL:
                # Must have a bet to call
                if state.current_bet <= player.current_bet:
                    raise THErrors.NO_BET_TO_CALL.create(
                        details={"player_id": move.player_id, "current_bet": state.current_bet, "player_bet": player.current_bet},
                    )

                call_amount = state.current_bet - player.current_bet
                actual_call = min(call_amount, player.chips)

                # If player doesn't have enough chips, they go all-in
                forced_all_in = actual_call < call_amount
                if forced_all_in:
                    player.status = PlayerStatus.ALL_IN
                    status_change_reason = PlayerStatusChangeReason.INSUFFICIENT_CHIPS

                player.chips -= actual_call
                player.current_bet += actual_call
                player.total_bet += actual_call

                # Add the call amount to the pot
                state.pot += actual_call

            case TexasHoldemAction.RAISE:
                if move.data.amount is None:
                    raise THErrors.MISSING_AMOUNT.create(message="Raise requires an amount", details={"player_id": move.player_id})

                previous_bet = state.current_bet

                # Determine minimum raise amount
                min_raise_amount = state.last_raise_amount if state.last_raise_amount > 0 else self.config.min_raise or self.config.big_blind
                min_total = previous_bet + min_raise_amount

                if move.data.amount < min_total:
                    raise THErrors.RAISE_TOO_SMALL.create(
                        message=f"Minimum raise is {min_raise_amount} - must bet at least {min_total}",
                        details={"minimum_raise": min_raise_amount, "minimum_total": min_total, "attempted": move.data.amount},
                    )

                # Check maximum raise if configured
                if self.config.max_raise is not None:
                    max_total = state.current_bet + self.config.max_raise
                    if move.data.amount > max_total:
                        raise THErrors.RAISE_TOO_LARGE.create(
                            message=f"Raise cannot exceed {self.config.max_raise}",
                            details={"maximum": self.config.max_raise, "attempted": move.data.amount - state.current_bet},
                        )

                # Calculate how much more the player needs to bet to reach the raise amount
                additional_bet = move.data.amount - player.current_bet
                actual_additional = min(additional_bet, player.chips)

                # If player doesn't have enough chips for full raise, they go all-in
                if actual_additional < additional_bet or actual_additional == player.chips:
                    return self._apply_move(
                        state,
                        PlayerMove(player_id=move.player_id, data=TexasHoldemMoveData(action=TexasHoldemAction.ALL_IN)),
                        event_collector,
                    )

                player.chips -= actual_additional
                player.current_bet += actual_additional
                player.total_bet += actual_additional

                # Add the additional bet amount to the pot
                state.pot += actual_additional
                state.current_bet = player.current_bet

                # The last_raise_amount is the conceptual increment of the raise,
                # calculated as the new total bet minus the previous total bet.
                state.last_raise_amount = state.current_bet - previous_bet
                state.last_raise_position = state.action_position

            case TexasHoldemAction.ALL_IN:
                all_in_amount = player.chips

                player.status = PlayerStatus.ALL_IN
                status_change_reason = PlayerStatusChangeReason.ALL_IN_ACTION

                player.chips = 0
                player.current_bet += all_in_amount
                player.total_bet += all_in_amount

                # Add the all-in amount to the pot
                state.pot += all_in_amount

                # Check if this all-in constitutes a raise
                if player.current_bet > state.current_bet:
                    previous_bet = state.current_bet
                    state.current_bet = player.current_bet

                    # Calculate the size of this all-in raise
                    raise_increment = state.current_bet - previous_bet

                    # Determine what a minimum raise would have been at this moment
                    min_raise_amount = state.last_raise_amount if state.last_raise_amount > 0 else self.config.min_raise or self.config.big_blind

                    # ONLY update last_raise_amount if the all-in was a full, legal raise.
                    # This is the crucial rule for incomplete raises.
                    if raise_increment >= min_raise_amount:
                        state.last_raise_amount = raise_increment

                    state.last_raise_position = state.action_position

        # Determine if this was a forced all-in (for actions other than explicit ALL_IN)

        forced_all_in = move.data.action != TexasHoldemAction.ALL_IN and player.status == PlayerStatus.ALL_IN and status_before != PlayerStatus.ALL_IN

        event_collector.add(
            PlayerActionEvent(
                turn=state.turn,
                player_id=move.player_id,
                action=move.data.action,
                amount=move.data.amount,
                player_chips_before=chips_before,
                player_chips_after=player.chips,
                player_bet_before=bet_before,
                player_bet_after=player.current_bet,
                forced_all_in=forced_all_in,
                status_before=status_before,
                status_after=player.status,
                status_change_reason=status_change_reason,
            )
        )

        # Emit pot update event if pot changed
        if state.pot != pot_before:
            amount_added = state.pot - pot_before
            event_collector.add(
                PotUpdateEvent(
                    turn=state.turn,
                    pot_before=pot_before,
                    pot_after=state.pot,
                    amount_added=amount_added,
                    current_bet_before=current_bet_before,
                    current_bet_after=state.current_bet,
                )
            )

        # Add current position to acted positions

        if state.action_position not in state.acted_positions:
            state.acted_positions.append(state.action_position)

        return None

    def _find_next_action_position(self, state: TexasHoldemState) -> int | None:
        """Find the next player to act from the current action position in the current round."""

        next_action_position: int | None = None
        for i in range(1, len(state.players)):
            position = (state.action_position + i) % len(state.players)
            next_player = state.players[position]

            # This player needs to act if they are active and haven't acted this round or their bet is less than the current bet.
            if next_player.status == PlayerStatus.ACTIVE and (position not in state.acted_positions or next_player.current_bet < state.current_bet):
                next_action_position = position
                break

        return next_action_position

    def _advance_betting_round(
        self,
        state: TexasHoldemState,
        event_collector: EventCollector[TexasHoldemEvent],
        players_in_hand: list[TexasHoldemPlayer],
        active_players: list[TexasHoldemPlayer],
    ) -> None:
        """Advance to the next betting round."""

        all_in_players = [p for p in players_in_hand if p.status == PlayerStatus.ALL_IN]
        if len(all_in_players) > 0:
            # TODO: Only create side pots when someone actually goes all-in, not on every round
            self._create_side_pots(state, event_collector, players_in_hand)

        cards_to_deal = 0
        next_round: BettingRound

        # If no active players remain, go to showdown.
        # It can be 0 if the player that just acted was the last one to go all-in.
        # It can be 1 if the player that just acted did not go all-in, but everyone else did.
        # If 2 or more active players remain, advance to the next betting round as usual.
        if len(active_players) <= 1 and len(all_in_players) > 0:
            cards_to_deal = 5 - len(state.community_cards)
            next_round = BettingRound.SHOWDOWN
        else:
            match state.betting_round:
                case BettingRound.PREFLOP:
                    cards_to_deal = 3
                    next_round = BettingRound.FLOP
                case BettingRound.FLOP:
                    cards_to_deal = 1
                    next_round = BettingRound.TURN
                case BettingRound.TURN:
                    cards_to_deal = 1
                    next_round = BettingRound.RIVER
                case BettingRound.RIVER:
                    cards_to_deal = 0
                    next_round = BettingRound.SHOWDOWN
                case _:
                    raise THErrors.VALIDATION_ERROR.create(
                        message=f"Invalid betting round: {state.betting_round.value}",
                        details={"betting_round": state.betting_round.value},
                    )

        # Deal community cards and emit events
        if cards_to_deal > 0:
            cards_dealt: list[Card] = []
            for _ in range(cards_to_deal):
                card = state.deck.pop()
                state.community_cards.append(card)
                cards_dealt.append(card)

            # Determine deal type
            deal_type = "runout"  # Default for multiple cards to showdown
            if next_round == BettingRound.FLOP:
                deal_type = "flop"
            elif next_round == BettingRound.TURN:
                deal_type = "turn"
            elif next_round == BettingRound.RIVER:
                deal_type = "river"

            # Emit community cards dealt event
            event_collector.add(
                CommunityCardsDealtEvent(
                    turn=state.turn,
                    cards=cards_dealt,
                    deal_type=deal_type,
                    total_community_cards=len(state.community_cards),
                )
            )

        # Emit betting round advanced event
        from_round = state.betting_round
        state.betting_round = next_round

        next_player_id = None
        if next_round != BettingRound.SHOWDOWN:
            self._init_new_round(state, event_collector)
            next_player_id = state.current_player_id

        event_collector.add(
            BettingRoundAdvancedEvent(
                turn=state.turn,
                from_round=from_round,
                to_round=next_round,
                next_player_id=next_player_id,
            )
        )

    def _init_new_round(self, state: TexasHoldemState, event_collector: EventCollector[TexasHoldemEvent]) -> None:
        """Initialize round-specific state including blinds, positions, and betting.

        Args:
            state: The game state to initialize
            event_collector: Collector for game events
        """

        # Clear round-specific state
        state.last_raise_amount = 0
        state.last_raise_position = None
        state.acted_positions = []

        for player in state.players:
            player.current_bet = 0

        active_indices = [i for i, p in enumerate(state.players) if p.status != PlayerStatus.OUT]
        num_active = len(active_indices)

        if num_active < 2:
            raise THErrors.INVALID_GAME_STATE.create(
                message="Not enough active players",
                details={"active_players": num_active},
            )

        state.dealer_position = self.config.default_dealer_position if state.turn == 1 else (state.dealer_position + 1) % num_active

        if state.betting_round == BettingRound.PREFLOP:
            if num_active == 2:
                # Special rules for heads-up games (2 active players)
                # In preflop, dealer is small blind and acts first
                state.small_blind_position = state.dealer_position
                state.big_blind_position = active_indices[(active_indices.index(state.dealer_position) + 1) % num_active]
                state.action_position = state.dealer_position
            else:
                # In preflop, small blind is next to dealer, then big blind, then action (UTG)
                dealer_idx_in_active = active_indices.index(state.dealer_position)
                state.small_blind_position = active_indices[(dealer_idx_in_active + 1) % num_active]
                state.big_blind_position = active_indices[(dealer_idx_in_active + 2) % num_active]
                state.action_position = active_indices[(dealer_idx_in_active + 3) % num_active]

            # In preflop, post blinds and deduct from chips
            small_blind_player = state.players[state.small_blind_position]
            big_blind_player = state.players[state.big_blind_position]

            # Handle small blind posting with insufficient chips
            actual_small_blind = min(self.config.small_blind, small_blind_player.chips)
            small_blind_forced_all_in = actual_small_blind != self.config.small_blind
            small_blind_player.current_bet = actual_small_blind
            small_blind_player.total_bet = actual_small_blind
            small_blind_player.chips -= actual_small_blind
            if small_blind_forced_all_in:
                small_blind_player.status = PlayerStatus.ALL_IN

            # Handle big blind posting with insufficient chips
            actual_big_blind = min(self.config.big_blind, big_blind_player.chips)
            big_blind_forced_all_in = actual_big_blind != self.config.big_blind
            big_blind_player.current_bet = actual_big_blind
            big_blind_player.total_bet = actual_big_blind
            big_blind_player.chips -= actual_big_blind
            if big_blind_forced_all_in:
                big_blind_player.status = PlayerStatus.ALL_IN

            event_collector.add(
                HandStartedEvent(
                    turn=state.turn,
                    dealer_position=state.dealer_position,
                    small_blind_position=state.small_blind_position,
                    big_blind_position=state.big_blind_position,
                    small_blind_amount=actual_small_blind,
                    big_blind_amount=actual_big_blind,
                    small_blind_forced_all_in=small_blind_forced_all_in,
                    big_blind_forced_all_in=big_blind_forced_all_in,
                )
            )

            state.pot = actual_small_blind + actual_big_blind

            # The current bet is still considered the big blind, even if the big blind player did not have enough chips to post it
            state.current_bet = self.config.big_blind
        else:
            if num_active == 2:
                # Special rules for heads-up games (2 active players)
                # In post-flop, big blind acts first. It must be active otherwise this method wouldn't be called.
                if state.players[state.big_blind_position].status != PlayerStatus.ACTIVE:
                    raise THErrors.INVALID_GAME_STATE.create(
                        message="Big blind is not active",
                        details={"big_blind_position": state.big_blind_position},
                    )
                state.action_position = state.big_blind_position
            else:
                # In post-flop, small blind acts first if they are active, otherwise next active player
                state.action_position = (
                    state.small_blind_position
                    if state.players[state.small_blind_position].status == PlayerStatus.ACTIVE
                    else active_indices[(active_indices.index(state.small_blind_position) + 1) % num_active]
                )

            state.current_bet = 0

        state.current_player_id = state.players[state.action_position].player_id

        # Shuffle deck
        state.deck = self._shuffle_deck()

        # Deal hole cards to active players
        player_cards: dict[PlayerId, list[Card]] = {}
        for player in state.players:
            if player.status != PlayerStatus.OUT:
                hole_cards = [state.deck.pop(), state.deck.pop()]
                player.hole_cards = hole_cards
                player_cards[player.player_id] = hole_cards

        # Emit hole cards dealt event
        if player_cards:
            event_collector.add(
                HoleCardsDealtEvent(
                    turn=state.turn,
                    player_cards=player_cards,
                )
            )

    def _shuffle_deck(self) -> list[Card]:
        deck = _DECK.copy()
        random.shuffle(deck)
        return deck

    def _evaluate_hand(self, cards: list[Card]) -> HandResult:
        """Evaluate a poker hand and return the result."""
        if len(cards) != 7:
            raise ValueError("Hand evaluation requires exactly 7 cards (2 hole cards + 5 community cards)")

        # Check all possible 5-card combinations and return the best hand
        best_result = None

        for five_cards in combinations(cards, 5):
            result = self._evaluate_five_card_hand(list(five_cards))
            if best_result is None or result.rank > best_result.rank or (result.rank == best_result.rank and result.high_cards > best_result.high_cards):
                best_result = result

        # This should never be None since we always have at least a high card
        if best_result is None:
            raise ValueError("Failed to evaluate hand - this should never happen")
        return best_result

    def _evaluate_five_card_hand(self, cards: list[Card]) -> HandResult:
        """Evaluate exactly 5 cards and return the result."""
        # Sort cards by rank in descending order
        sorted_cards = sorted(cards, key=lambda c: c.rank.as_int(), reverse=True)

        # Check for each hand type from highest to lowest
        result = self._check_royal_flush(sorted_cards)
        if result:
            return result

        result = self._check_straight_flush(sorted_cards)
        if result:
            return result

        result = self._check_four_of_a_kind(sorted_cards)
        if result:
            return result

        result = self._check_full_house(sorted_cards)
        if result:
            return result

        result = self._check_flush(sorted_cards)
        if result:
            return result

        result = self._check_straight(sorted_cards)
        if result:
            return result

        result = self._check_three_of_a_kind(sorted_cards)
        if result:
            return result

        result = self._check_two_pair(sorted_cards)
        if result:
            return result

        result = self._check_one_pair(sorted_cards)
        if result:
            return result

        # High card
        return self._check_high_card(sorted_cards)

    def _get_best_five_card_hand(self, cards: list[Card]) -> list[Card]:
        """Get the best 5-card hand from available cards."""
        if len(cards) == 5:
            return cards

        # For now, just return the 5 highest cards
        # In a full implementation, we'd check all combinations
        return sorted(cards, key=lambda c: c.rank.as_int(), reverse=True)[:5]

    def _check_royal_flush(self, cards: list[Card]) -> HandResult | None:
        """Check for royal flush (A, K, Q, J, 10 of same suit)."""
        if not self._is_flush(cards):
            return None

        ranks = [c.rank.as_int() for c in cards]
        if sorted(ranks, reverse=True) == [14, 13, 12, 11, 10]:
            return HandResult(rank=HandRank.ROYAL_FLUSH, high_cards=[self._find_card_by_rank(cards, 14)], description="Royal Flush")
        return None

    def _check_straight_flush(self, cards: list[Card]) -> HandResult | None:
        """Check for straight flush."""
        if not self._is_flush(cards):
            return None

        straight_high = self._get_straight_high_card(cards)
        if straight_high:
            return HandResult(rank=HandRank.STRAIGHT_FLUSH, high_cards=[straight_high], description="Straight Flush")
        return None

    def _check_four_of_a_kind(self, cards: list[Card]) -> HandResult | None:
        """Check for four of a kind."""
        rank_counts = self._get_rank_counts(cards)

        for rank, count in rank_counts.items():
            if count == 4:
                kicker = max(r for r, _ in rank_counts.items() if r != rank)
                four_card = self._find_card_by_rank(cards, rank)
                kicker_card = self._find_card_by_rank(cards, kicker)
                return HandResult(rank=HandRank.FOUR_OF_A_KIND, high_cards=[four_card, kicker_card], description="Four of a Kind")
        return None

    def _check_full_house(self, cards: list[Card]) -> HandResult | None:
        """Check for full house."""
        rank_counts = self._get_rank_counts(cards)

        trips = None
        pair = None

        for rank, count in sorted(rank_counts.items(), reverse=True):
            if count == 3 and trips is None:
                trips = rank
            elif count == 2 and pair is None:
                pair = rank

        if trips and pair:
            trips_card = self._find_card_by_rank(cards, trips)
            pair_card = self._find_card_by_rank(cards, pair)
            return HandResult(rank=HandRank.FULL_HOUSE, high_cards=[trips_card, pair_card], description="Full House")
        return None

    def _check_flush(self, cards: list[Card]) -> HandResult | None:
        """Check for flush."""
        if self._is_flush(cards):
            sorted_cards = sorted(cards, key=lambda c: c.rank.as_int(), reverse=True)
            return HandResult(rank=HandRank.FLUSH, high_cards=sorted_cards, description="Flush")
        return None

    def _check_straight(self, cards: list[Card]) -> HandResult | None:
        """Check for straight."""
        straight_high = self._get_straight_high_card(cards)
        if straight_high:
            # Find the actual card with the straight high rank
            high_card = next((card for card in cards if card.rank.as_int() == straight_high), cards[0])
            return HandResult(rank=HandRank.STRAIGHT, high_cards=[high_card], description="Straight")
        return None

    def _check_three_of_a_kind(self, cards: list[Card]) -> HandResult | None:
        """Check for three of a kind."""
        rank_counts = self._get_rank_counts(cards)

        for rank, count in rank_counts.items():
            if count == 3:
                kickers = sorted([r for r, _ in rank_counts.items() if r != rank], reverse=True)
                trips_card = self._find_card_by_rank(cards, rank)
                kicker_cards = self._get_cards_by_ranks(cards, kickers)
                return HandResult(
                    rank=HandRank.THREE_OF_A_KIND,
                    high_cards=[trips_card, *kicker_cards],
                    description="Three of a Kind",
                )
        return None

    def _check_two_pair(self, cards: list[Card]) -> HandResult | None:
        """Check for two pair."""
        rank_counts = self._get_rank_counts(cards)

        pairs = [rank for rank, count in rank_counts.items() if count == 2]
        if len(pairs) >= 2:
            pairs.sort(reverse=True)
            kicker = max(r for r, _ in rank_counts.items() if r not in pairs[:2])
            pair1_card = self._find_card_by_rank(cards, pairs[0])
            pair2_card = self._find_card_by_rank(cards, pairs[1])
            kicker_card = self._find_card_by_rank(cards, kicker)
            return HandResult(
                rank=HandRank.TWO_PAIR,
                high_cards=[pair1_card, pair2_card, kicker_card],
                description="Two Pair",
            )
        return None

    def _check_one_pair(self, cards: list[Card]) -> HandResult | None:
        """Check for one pair."""
        rank_counts = self._get_rank_counts(cards)

        for rank, count in rank_counts.items():
            if count == 2:
                kickers = sorted([r for r, _ in rank_counts.items() if r != rank], reverse=True)
                pair_card = self._find_card_by_rank(cards, rank)
                kicker_cards = self._get_cards_by_ranks(cards, kickers)
                return HandResult(rank=HandRank.PAIR, high_cards=[pair_card, *kicker_cards], description="Pair")
        return None

    def _check_high_card(self, cards: list[Card]) -> HandResult:
        """Return high card result."""
        sorted_cards = sorted(cards, key=lambda c: c.rank.as_int(), reverse=True)
        return HandResult(rank=HandRank.HIGH_CARD, high_cards=sorted_cards[:5], description="High Card")

    def _is_flush(self, cards: list[Card]) -> bool:
        """Check if all cards are the same suit."""
        return len({c.suit for c in cards}) == 1

    def _get_straight_high_card(self, cards: list[Card]) -> Card | None:
        """Get the high card of a straight, or None if not a straight."""
        ranks = sorted({c.rank.as_int() for c in cards}, reverse=True)

        # Check for regular straight
        if len(ranks) >= 5:
            for i in range(len(ranks) - 4):
                if ranks[i] - ranks[i + 4] == 4:
                    return self._find_card_by_rank(cards, ranks[i])

        # Check for wheel (A-2-3-4-5)
        if set(ranks) >= {14, 2, 3, 4, 5}:
            return self._find_card_by_rank(cards, 5)  # In wheel, 5 is the high card

        return None

    def _get_rank_counts(self, cards: list[Card]) -> dict[int, int]:
        """Get count of each rank in the hand."""
        counts: dict[int, int] = {}
        for card in cards:
            r = card.rank.as_int()
            counts[r] = counts.get(r, 0) + 1
        return counts

    def _find_card_by_rank(self, cards: list[Card], rank: int) -> Card:
        card = next((c for c in cards if c.rank.as_int() == rank), None)
        if card is None:
            raise THErrors.INVALID_GAME_STATE.create(f"No card found with rank {rank}")
        return card

    def _get_cards_by_ranks(self, cards: list[Card], ranks: list[int]) -> list[Card]:
        """Get cards with the specified ranks from the hand, in order of ranks."""
        result: list[Card] = []
        for rank in ranks:
            rank_cards = [card for card in cards if card.rank.as_int() == rank]
            if rank_cards:
                result.append(rank_cards[0])  # Take first card of this rank
        return result

    def _create_side_pots(self, state: TexasHoldemState, event_collector: EventCollector[TexasHoldemEvent], players_in_hand: list[TexasHoldemPlayer]) -> None:
        """Create side pots when players have different all-in amounts."""
        all_in_players = [p for p in players_in_hand if p.status == PlayerStatus.ALL_IN]

        # Only create side pots if there are all-in players
        if len(all_in_players) == 0:
            return

        # Get all unique bet amounts from all players (including active players)
        bet_amounts = sorted({p.total_bet for p in players_in_hand if p.total_bet > 0})

        # If all players have the same bet amount, no side pots needed
        if len(bet_amounts) <= 1:
            return

        # Clear existing side pots, we will recalculate them
        state.side_pots = []

        # Create side pots for each betting level
        prev_amount = 0
        for amount in bet_amounts:
            # Find players eligible for this side pot level
            # Players with this bet amount or higher are eligible
            eligible_players = [player.player_id for player in players_in_hand if player.total_bet >= amount]

            # Calculate side pot amount based on the difference from previous level
            level_contribution = amount - prev_amount
            side_pot_amount = level_contribution * len(eligible_players)

            # Only create side pot if there's an amount and eligible players
            if side_pot_amount > 0 and len(eligible_players) > 0:
                side_pot = SidePot(amount=side_pot_amount, eligible_players=eligible_players)
                state.side_pots.append(side_pot)

            prev_amount = amount

        # Adjust main pot to be zero since side pots now contain all the money
        if state.side_pots:
            state.pot = 0

            # Emit side pots created event
            event_collector.add(
                SidePotsCreatedEvent(
                    turn=state.turn,
                    side_pots=state.side_pots,
                    main_pot_amount=state.pot,
                )
            )

    def _finalize_game(self, state: TexasHoldemState, event_collector: EventCollector[TexasHoldemEvent], players_in_hand: list[TexasHoldemPlayer]) -> None:
        """Finalize the game by determining winners and distributing chips."""

        if len(players_in_hand) == 1:
            # Only one player left, they win
            winner = players_in_hand[0]
            state.winners = [winner.player_id]
            # Create a proper HandResult for uncontested win
            uncontested_result = HandResult(
                rank=HandRank.HIGH_CARD,  # Use a default rank
                high_cards=[],
                description="Uncontested",
            )
            state.winning_hands = {winner.player_id: uncontested_result}

            # Emit winners announced event
            event_collector.add(
                WinnersAnnouncedEvent(
                    turn=state.turn,
                    winners=state.winners,
                    winning_hands=state.winning_hands,
                    uncontested=True,
                )
            )
        else:
            # Multiple players, evaluate hands for all players in hand
            player_hands: dict[PlayerId, tuple[TexasHoldemPlayer, HandResult]] = {}
            for player in players_in_hand:
                all_cards = player.hole_cards + state.community_cards
                hand_result = self._evaluate_hand(all_cards)
                player_hands[player.player_id] = (player, hand_result)

                # Emit hand evaluated event for each player
                best_five_cards = self._get_best_five_card_hand(all_cards)
                event_collector.add(
                    HandEvaluatedEvent(
                        turn=state.turn,
                        player_id=player.player_id,
                        hand_result=hand_result,
                        final_hand=best_five_cards,
                    )
                )

            # Store all evaluated hands for side pot distribution
            state.winning_hands = {player_id: hand_result for player_id, (_, hand_result) in player_hands.items()}

            # For overall winners (used for display), find the best hand among all players
            best_rank: HandRank = max(hand_result.rank for _, hand_result in player_hands.values())
            best_players: list[tuple[TexasHoldemPlayer, HandResult]] = [
                (player, hand_result) for player, hand_result in player_hands.values() if hand_result.rank == best_rank
            ]

            if len(best_players) == 1:
                # Single overall winner
                winner_player, _ = best_players[0]
                state.winners = [winner_player.player_id]
            else:
                # Multiple players with same rank, compare high cards
                best_high_cards = max(hand_result.high_cards for _, hand_result in best_players)
                final_winners: list[tuple[TexasHoldemPlayer, HandResult]] = [
                    (player, hand_result) for player, hand_result in best_players if hand_result.high_cards == best_high_cards
                ]
                state.winners = [player.player_id for player, _ in final_winners]

            # Emit winners announced event
            event_collector.add(
                WinnersAnnouncedEvent(
                    turn=state.turn,
                    winners=state.winners,
                    winning_hands=state.winning_hands,
                    uncontested=False,
                )
            )

        # Distribute chips to winners (handles side pots correctly)
        self._distribute_chips_to_winners(state, event_collector)

        # Reset current bets after chip distribution
        for player in state.players:
            player.current_bet = 0

        # Mark players as 'out' if they have no chips and emit status change events
        for player in state.players:
            if player.chips == 0 and player.status != PlayerStatus.OUT:
                old_status = player.status
                player.status = PlayerStatus.OUT
                event_collector.add(
                    PlayerStatusChangedEvent(
                        turn=state.turn,
                        player_id=player.player_id,
                        from_status=old_status,
                        to_status=PlayerStatus.OUT,
                        reason=PlayerStatusChangeReason.INSUFFICIENT_CHIPS,
                    )
                )

        state.is_finished = True

        # Emit game finished event
        final_chip_counts = {player.player_id: player.chips for player in state.players}
        event_collector.add(
            GameFinishedEvent(
                turn=state.turn,
                final_chip_counts=final_chip_counts,
            )
        )

    def _distribute_chips_to_winners(self, state: TexasHoldemState, event_collector: EventCollector[TexasHoldemEvent]) -> None:
        """Distribute chips to winners based on pot and side pots."""
        # Check if chips have already been distributed
        total_pot_amount = state.pot + sum(sp.amount for sp in state.side_pots)
        if total_pot_amount == 0:
            return

        # Track distributions for event emission
        distributions: list[dict[str, Any]] = []

        # Distribute main pot if it exists
        if state.pot > 0:
            if not state.winners:
                return
            chips_per_winner = state.pot // len(state.winners)
            remainder = state.pot % len(state.winners)

            for i, winner_id in enumerate(state.winners):
                winner = state.get_player_by_id(winner_id)
                amount = chips_per_winner
                # Give remainder to first winner(s)
                if i < remainder:
                    amount += 1

                winner.chips += amount

                distributions.append(
                    {
                        "player_id": winner_id,
                        "amount": amount,
                        "source": "main_pot",
                    }
                )

            state.pot = 0

        # Distribute side pots - each side pot has its own winner determination
        for side_pot_idx, side_pot in enumerate(state.side_pots):
            if side_pot.amount == 0:
                continue

            # Find the best hand among players eligible for this side pot
            eligible_hands: dict[PlayerId, HandResult] = {
                player_id: hand_result for player_id, hand_result in state.winning_hands.items() if player_id in side_pot.eligible_players
            }

            if not eligible_hands:
                continue

            # Find the best hand rank among eligible players
            best_rank = max(hand_result.rank for hand_result in eligible_hands.values())
            best_eligible_players = [player_id for player_id, hand_result in eligible_hands.items() if hand_result.rank == best_rank]

            # If multiple players have the same rank, compare high cards
            if len(best_eligible_players) > 1:
                best_high_cards = max(eligible_hands[player_id].high_cards for player_id in best_eligible_players)
                side_pot_winners = [player_id for player_id in best_eligible_players if eligible_hands[player_id].high_cards == best_high_cards]
            else:
                side_pot_winners = best_eligible_players

            # Distribute this side pot among its winners
            if side_pot_winners:
                chips_per_winner = side_pot.amount // len(side_pot_winners)
                remainder = side_pot.amount % len(side_pot_winners)

                for i, winner_id in enumerate(side_pot_winners):
                    winner = state.get_player_by_id(winner_id)
                    amount = chips_per_winner
                    # Give remainder to first winner(s)
                    if i < remainder:
                        amount += 1

                    winner.chips += amount

                    distributions.append(
                        {
                            "player_id": winner_id,
                            "amount": amount,
                            "source": f"side_pot_{side_pot_idx}",
                        }
                    )

                side_pot.amount = 0

        # Clear side pots after distribution
        state.side_pots = []

        # Emit chips distributed event if any distributions occurred
        if distributions:
            event_collector.add(
                ChipsDistributedEvent(
                    turn=state.turn,
                    distributions=distributions,
                )
            )

    @override
    def calc_possible_moves(self, state: TexasHoldemState, player_id: PlayerId) -> TexasHoldemPossibleMoves | None:
        """Calculate possible moves for a player.

        Args:
            state: Current game state
            player_id: Player ID to calculate moves for

        Returns:
            Possible moves for the player or None if not their turn
        """
        # Check if it's this player's turn
        if state.current_player_id != player_id or state.is_finished or state.betting_round == BettingRound.SHOWDOWN:
            return None

        player = state.get_player_by_id(player_id)

        # Check if player is active
        if player.status != PlayerStatus.ACTIVE:
            return None

        # Check if player has chips
        if player.chips == 0:
            return None

        possible_moves: list[TexasHoldemPossibleMove] = []

        # Fold is always possible
        possible_moves.append(TexasHoldemPossibleMove(action=TexasHoldemAction.FOLD))

        # Check if player can check
        if state.current_bet <= player.current_bet:
            possible_moves.append(TexasHoldemPossibleMove(action=TexasHoldemAction.CHECK))

        # Check if player can call
        if state.current_bet > player.current_bet:
            possible_moves.append(TexasHoldemPossibleMove(action=TexasHoldemAction.CALL))

        # Check if player can raise
        min_raise_amount = state.last_raise_amount if state.last_raise_amount > 0 else self.config.min_raise or self.config.big_blind
        min_total = state.current_bet + min_raise_amount

        # Player needs enough chips to make at least the minimum raise
        if player.chips + player.current_bet >= min_total:
            max_raise_amount = player.chips + player.current_bet
            if self.config.max_raise is not None:
                max_raise_amount = min(max_raise_amount, state.current_bet + self.config.max_raise)

            possible_moves.append(
                TexasHoldemPossibleMove(
                    action=TexasHoldemAction.RAISE,
                    min_raise_amount=min_total,
                    max_raise_amount=max_raise_amount,
                )
            )

        # All-in is always possible if player has chips
        if player.chips > 0:
            possible_moves.append(TexasHoldemPossibleMove(action=TexasHoldemAction.ALL_IN))

        return TexasHoldemPossibleMoves(possible_moves=possible_moves)

    @override
    def error_fallback_move(self, state: TexasHoldemState, event_collector: EventCollector[TexasHoldemEvent], player_id: PlayerId) -> TexasHoldemMoveData:
        """CHECK if possible, otherwise FOLD."""
        # Get possible moves for the current player
        possible_moves = self.calc_possible_moves(state, player_id)
        if possible_moves and possible_moves.possible_moves:
            # First, look for check action (preferred fallback)
            for move in possible_moves.possible_moves:
                if move.action == TexasHoldemAction.CHECK:
                    return TexasHoldemMoveData(action=TexasHoldemAction.CHECK)

        return TexasHoldemMoveData(action=TexasHoldemAction.FOLD)

    @override
    def get_player_view(self, state: TexasHoldemState, player_id: PlayerId, events: list[TexasHoldemEvent]) -> TexasHoldemStateView:
        # Find the current player
        current_player = state.get_player_by_id(player_id)

        # Calculate already_played_players and should_play_players based on game state
        already_played_players: list[TexasHoldemOtherPlayerView] = []
        should_play_players: list[TexasHoldemOtherPlayerView] = []

        for i, player in enumerate(state.players):
            if player.player_id == player_id:
                continue  # Skip the current player

            player_view = player.to_other_player_view()

            # Determine player categorization based on action status and bet matching
            if player.status == PlayerStatus.ACTIVE:
                # Active players who still need to act:
                # 1. Haven't acted this round yet, OR
                # 2. Have acted but their current bet is less than the current bet (due to raises)
                if i not in state.acted_positions or player.current_bet < state.current_bet:
                    should_play_players.append(player_view)
                else:
                    # Have acted and their bet matches current bet - they're caught up
                    already_played_players.append(player_view)
            elif player.status != PlayerStatus.OUT:
                # Players who are folded or all-in are considered "already played"
                already_played_players.append(player_view)

        # Convert events to player view events
        player_view_events: list[TexasHoldemPlayerViewEvent] = [
            view_event for event in events if (view_event := self._convert_to_player_view_event(event, player_id)) is not None
        ]

        return TexasHoldemStateView(
            betting_round=state.betting_round,
            community_cards=state.community_cards,
            me=current_player,
            already_played_players=already_played_players,
            should_play_players=should_play_players,
            pot=state.pot,
            side_pots=state.side_pots,
            current_bet=state.current_bet,
            dealer_position=state.dealer_position,
            small_blind_position=state.small_blind_position,
            big_blind_position=state.big_blind_position,
            last_raise_amount=state.last_raise_amount,
            last_raise_position=state.last_raise_position,
            winners=state.winners,
            winning_hands=state.winning_hands,
            events=player_view_events,
        )

    def _convert_to_player_view_event(self, event: TexasHoldemEvent, viewer_id: PlayerId) -> TexasHoldemPlayerViewEvent | None:
        """Convert a game event to a player view event, filtering sensitive information."""
        match event:
            case GameInitializedEvent():
                return None

            case PlayerJoinedEvent():
                return PlayerJoinedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    player_id=event.player_id,
                    name=event.name,
                )

            case PlayerLeftEvent():
                return PlayerLeftPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    player_id=event.player_id,
                    reason=event.reason,
                )

            case PlayerStatusChangedEvent():
                return PlayerStatusChangedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    player_id=event.player_id,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    reason=event.reason,
                )

            case HandStartedEvent():
                return HandStartedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    dealer_position=event.dealer_position,
                    small_blind_position=event.small_blind_position,
                    big_blind_position=event.big_blind_position,
                    small_blind_amount=event.small_blind_amount,
                    big_blind_amount=event.big_blind_amount,
                    small_blind_forced_all_in=event.small_blind_forced_all_in,
                    big_blind_forced_all_in=event.big_blind_forced_all_in,
                )

            case HoleCardsDealtEvent():
                # Only show if viewer has cards in this event
                if viewer_id not in event.player_cards:
                    return None
                return HoleCardsDealtPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    my_cards=event.player_cards[viewer_id],
                )

            case PlayerActionEvent():
                return PlayerActionPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    player_id=event.player_id,
                    action=event.action,
                    amount=event.amount,
                    player_chips_before=event.player_chips_before,
                    player_chips_after=event.player_chips_after,
                    player_bet_before=event.player_bet_before,
                    player_bet_after=event.player_bet_after,
                    forced_all_in=event.forced_all_in,
                    thinking_time_ms=event.thinking_time_ms,
                    status_before=event.status_before,
                    status_after=event.status_after,
                    status_change_reason=event.status_change_reason,
                )

            case PotUpdateEvent():
                return PotUpdatePlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    pot_before=event.pot_before,
                    pot_after=event.pot_after,
                    amount_added=event.amount_added,
                    current_bet_before=event.current_bet_before,
                    current_bet_after=event.current_bet_after,
                )

            case BettingRoundAdvancedEvent():
                return BettingRoundAdvancedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    from_round=event.from_round,
                    to_round=event.to_round,
                    next_player_id=event.next_player_id,
                )

            case CommunityCardsDealtEvent():
                return CommunityCardsDealtPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    cards=event.cards,
                    deal_type=event.deal_type,
                    total_community_cards=event.total_community_cards,
                )

            case SidePotsCreatedEvent():
                return SidePotsCreatedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    side_pots=event.side_pots,
                    main_pot_amount=event.main_pot_amount,
                )

            case WinnersAnnouncedEvent():
                return WinnersAnnouncedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    winners=event.winners,
                    winning_hands=event.winning_hands,
                    uncontested=event.uncontested,
                )

            case ChipsDistributedEvent():
                return ChipsDistributedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    distributions=event.distributions,
                )

            case GameFinishedEvent():
                return GameFinishedPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    final_chip_counts=event.final_chip_counts,
                )

            case AgentReasoningEvent():
                # Only show reasoning events to the player who made them
                if event.player_id != viewer_id:
                    return None
                return AgentReasoningPlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    player_id=event.player_id,
                    reasoning=event.reasoning,
                )

            case ChatMessageEvent():
                # Show all chat messages to all players
                return ChatMessagePlayerViewEvent(
                    timestamp=event.timestamp,
                    turn=event.turn,
                    player_id=event.player_id,
                    message=event.message,
                )

            case HandEvaluatedEvent():
                # Skip hand evaluation events (internal details)
                return None

    @override
    @classmethod
    def get_state_generation_system_prompt(cls) -> str:
        """Get system prompt for Texas Hold'em state generation."""
        return (
            "You will generate a valid Texas Hold'em player-view JSON. "
            "Follow the provided JSON Schema exactly (keys are camelCase). "
            "Only return the JSON object, with no extra text."
        )

    @override
    @classmethod
    def create_state_generation_user_prompt(cls, description: str) -> str:
        """Create user prompt for Texas Hold'em state generation with variety instructions."""
        return f"""Generate a realistic and varied Texas Hold'em game state based on this description: {description}

VARIATION REQUIREMENTS:
- Randomize the number of players (2-9 players total)
- Vary stack sizes: some players short (10-20 BB), medium (30-60 BB), or deep (100+ BB)
- Use different betting rounds (preflop, flop, turn, river) based on the scenario
- Randomize dealer position and player positions
- Create realistic pot sizes and betting patterns
- Use diverse community card combinations
- Vary player statuses (some folded, some active, maybe all-in players)

Make the scenario feel authentic and different each time, while matching the user's description."""

    @override
    @classmethod
    def get_state_generation_examples(cls) -> list[str]:
        return [
            "Generate a minimal valid Texas Hold'em state with two players and blinds posted.",
            "Create a 6-max flop situation with a strong combo draw; include stacks, positions, pot and action so far.",
            "Short stack push/fold decision with 12 big blinds in the cutoff; preflop setup.",
            "Button steal spot vs a tight SB and aggressive BB; use realistic stacks and blinds.",
        ]

    @override
    @classmethod
    def validate_generated_state(cls, state_data: dict[str, Any]) -> TexasHoldemStateView:
        """Validate and convert generated state data to TexasHoldemStatePlayerView."""
        try:
            # Validate against Pydantic model
            validated_state = TexasHoldemStateView.model_validate(state_data)
            return validated_state

        except Exception as e:
            raise ValueError(f"Generated state is invalid: {e}") from e

    @override
    @classmethod
    def validate_test_json(cls, state_view: TexasHoldemStateView) -> TexasHoldemStateView:
        """Environment-specific validation for poker test JSON.

        Goals:
        - Ensure uniqueness and role consistency across me/already_played/should_play lists
        - Ensure players marked as already_played actually have a previous_action
        - Ensure players who still need to act are not marked as already_played
        - Basic sanity around folded/all_in statuses and should_play list
        """
        view = state_view

        # 1) Uniqueness across buckets
        ids: set[object] = set()

        def check_and_add(pid: object, bucket: str) -> None:
            if pid in ids:
                raise ValueError(f"Duplicate player_id {pid} across view buckets (in {bucket})")
            ids.add(pid)

        check_and_add(view.me.player_id, "me")
        for p in view.already_played_players:
            check_and_add(p.player_id, "already_played_players")
        for p in view.should_play_players:
            check_and_add(p.player_id, "should_play_players")

        # 2) already_played must have previous_action
        for p in view.already_played_players:
            if p.previous_action is None:
                raise ValueError(f"Player {p.player_id} is in already_played_players but has no previous_action")

        # 3) Players who still need to act should not be in already_played
        # If current_bet>0 then an ACTIVE player with current_bet<state.current_bet still needs to act
        for p in view.already_played_players:
            if p.status == PlayerStatus.ACTIVE and p.current_bet < view.current_bet:
                raise ValueError(
                    f"Player {p.player_id} has not matched current bet (current_bet={p.current_bet} < table current_bet={view.current_bet}) "
                    "— they should be in should_play_players, not already_played_players"
                )

        # 4) Players required to play should not be folded
        for p in view.should_play_players:
            if p.status == PlayerStatus.FOLDED:
                raise ValueError(f"Player {p.player_id} is FOLDED but appears in should_play_players")

        return view

    @override
    @classmethod
    def extract_game_result(cls, state: TexasHoldemState) -> GameResult:
        """Extract game result information from Texas Hold'em state."""
        # Get final chip counts from GameFinishedEvent if available
        final_scores = None
        if state.is_finished:
            # Build final scores from player chip counts
            final_scores = {player.player_id: player.chips for player in state.players}

        return GameResult(
            winner_id=None,  # Texas Hold'em can have multiple winners
            winners_ids=list(state.winners) if state.winners else [],
            draw_reason=None,  # Texas Hold'em doesn't have draws
            final_scores=final_scores,
        )

    @override
    def on_player_left(
        self,
        state: TexasHoldemState,
        leaving_player_id: PlayerId,
        event_collector: EventCollector[TexasHoldemEvent],
    ) -> FinishDecision:
        """Handle a player leaving the Texas Hold'em game.

        Emits a PlayerLeftEvent and determines whether the game should finish.
        For poker, the game can continue with remaining players if above minimum.

        Args:
            state: Current poker game state
            leaving_player_id: ID of the player who is leaving
            event_collector: Collector for events to emit

        Returns:
            FinishDecision indicating whether game should continue, finish, or be cancelled
        """
        # Emit PlayerLeftEvent
        event = PlayerLeftEvent(
            player_id=leaving_player_id,
            reason="user_initiated",
            turn=state.turn,
        )
        event_collector.add(event)

        # Count remaining active players (not OUT and not the leaving player)
        remaining_active_players = [p for p in state.players if p.player_id != leaving_player_id and p.status != PlayerStatus.OUT]

        if len(remaining_active_players) == 0:
            # No players left - cancel the game
            return FinishDecision.CANCEL
        else:
            # For poker, we always continue the game when players leave
            # The service layer will handle adding system agents if needed
            # We only finish if all remaining players are system agents (handled by service)
            return FinishDecision.CONTINUE

    @override
    def finish_due_to_forfeit(
        self,
        state: TexasHoldemState,
        remaining_player_ids: list[PlayerId],
        event_collector: EventCollector[TexasHoldemEvent],
    ) -> None:
        """Finish the poker game by declaring remaining players as winners.

        Modifies state in place to mark game as finished with remaining players as winners.

        Args:
            state: Poker game state to modify
            remaining_player_ids: IDs of players still in the game
            event_collector: Collector for any final events
        """
        # Mark game as finished
        state.is_finished = True

        # Set winners to all remaining players
        state.winners = remaining_player_ids

    @classmethod
    @override
    def get_tool_creation_context(cls) -> Any:
        """Get context for tool creation in Texas Hold'em environment.

        Returns:
            ToolCreationContext specialized for Texas Hold'em
        """
        from common.agents.models import ToolCreationContext, ToolExample

        return ToolCreationContext[TexasHoldemStateView, TexasHoldemPossibleMoves, TexasHoldemMoveData](
            environment=GameType.TEXAS_HOLDEM,
            state_schema=TexasHoldemStateView.model_json_schema(),
            possible_moves_schema=TexasHoldemPossibleMoves.model_json_schema(),
            move_data_schema=TexasHoldemMoveData.model_json_schema(),
            constraints=[
                "Tools must not access other players' hole cards (only visible in state view if shown down)",
                "Tools must handle all betting rounds: preflop, flop, turn, river",
                "Tools must account for player position and stack sizes",
                "Tools must respect pot and betting limits",
                "Tools cannot modify game state, only analyze it",
            ],
            best_practices=[
                "Calculate pot odds when evaluating calling decisions",
                "Consider position when evaluating hand strength",
                "Account for stack-to-pot ratio (SPR) in decision making",
                "Use hand equity calculations for drawing hands",
                "Consider opponent betting patterns when available",
                "Factor in tournament vs cash game dynamics if applicable",
            ],
            example_tools=[
                ToolExample(
                    name="pot_odds_calculator",
                    display_name="Pot Odds Calculator",
                    description="Calculate pot odds for calling decisions",
                    explanation="Calculates the ratio of current pot size to the cost of a call, helping determine if a call is profitable",
                    code='''def lambda_handler(event, context):
    """Calculate pot odds for calling decisions."""
    state = event["state"]

    # Get current pot and cost to call
    pot = state["pot"]
    current_bet = state["current_bet"]

    # Find our player
    player_id = event["player_id"]
    our_player = next(p for p in state["players"] if p["player_id"] == player_id)
    our_bet = our_player.get("current_bet", 0)

    # Calculate cost to call
    cost_to_call = current_bet - our_bet

    if cost_to_call <= 0:
        return {
            "pot_odds": 0,
            "pot_odds_percentage": 0,
            "message": "No cost to call (check or already called)"
        }

    # Calculate pot odds
    total_pot_after_call = pot + cost_to_call
    pot_odds = cost_to_call / total_pot_after_call
    pot_odds_percentage = pot_odds * 100

    return {
        "pot": pot,
        "cost_to_call": cost_to_call,
        "pot_odds": round(pot_odds, 4),
        "pot_odds_percentage": round(pot_odds_percentage, 2),
        "message": f"Need {pot_odds_percentage:.1f}% equity to call profitably"
    }
''',
                ),
                ToolExample(
                    name="hand_strength_evaluator",
                    display_name="Hand Strength Evaluator",
                    description="Evaluate current hand strength based on hole cards and community cards",
                    explanation="Analyzes hole cards and community cards to determine hand ranking and strength",
                    code='''def lambda_handler(event, context):
    """Evaluate hand strength."""
    state = event["state"]
    player_id = event["player_id"]

    # Find our player and get hole cards
    our_player = next(p for p in state["players"] if p["player_id"] == player_id)
    hole_cards = our_player.get("hole_cards", [])
    community_cards = state.get("community_cards", [])

    if not hole_cards:
        return {"error": "No hole cards available"}

    # Combine all cards
    all_cards = hole_cards + community_cards

    # Simple hand evaluation (you would use a proper poker hand evaluator library)
    ranks = [card["rank"] for card in all_cards]
    suits = [card["suit"] for card in all_cards]

    # Count rank occurrences
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1

    # Check for pairs, trips, quads
    max_of_kind = max(rank_counts.values()) if rank_counts else 0

    hand_type = "High Card"
    if max_of_kind == 4:
        hand_type = "Four of a Kind"
    elif max_of_kind == 3:
        hand_type = "Three of a Kind"
    elif max_of_kind == 2:
        pairs = sum(1 for count in rank_counts.values() if count == 2)
        hand_type = "Two Pair" if pairs == 2 else "One Pair"

    return {
        "hand_type": hand_type,
        "hole_cards": hole_cards,
        "community_cards": community_cards,
        "message": f"Current hand: {hand_type}"
    }
''',
                ),
            ],
            tool_creation_guidance="""
Texas Hold'em Tool Creation Guidelines:

**Input Structure:**
- Tools receive a `state` dict containing the TexasHoldemStateView
- Access player's hole cards via `state["players"]` filtered by `player_id`
- Community cards available in `state["community_cards"]`
- Pot information in `state["pot"]` and `state["current_bet"]`

**Common Tool Types:**
1. **Pot Odds Calculators**: Calculate ratio of pot to call cost
2. **Hand Evaluators**: Determine hand strength and ranking
3. **Equity Calculators**: Estimate win probability
4. **Betting Advisors**: Suggest optimal bet sizing
5. **Position Analyzers**: Evaluate position advantage

**Key Considerations:**
- Betting round affects available information (preflop vs river)
- Stack sizes relative to blinds matter (SPR)
- Position is crucial (early, middle, late, blinds)
- Tournament vs cash game dynamics differ

**Return Format:**
Tools should return a dictionary with:
- Calculated values (pot_odds, equity, etc.)
- Explanatory message
- Any relevant warnings or notes
""",
        )


class TexasHoldemEnvTypes(
    GameEnvTypes[TexasHoldemState, TexasHoldemStateView, TexasHoldemEvent, TexasHoldemMoveData, TexasHoldemConfig, TexasHoldemPossibleMoves]
):
    @override
    @classmethod
    def type(cls) -> GameType:
        return GameType.TEXAS_HOLDEM

    @override
    @classmethod
    def config_type(cls) -> type[TexasHoldemConfig]:
        return TexasHoldemConfig

    @override
    @classmethod
    def state_type(cls) -> type[TexasHoldemState]:
        return TexasHoldemState

    @override
    @classmethod
    def event_type(cls) -> type[TexasHoldemEvent]:
        return TexasHoldemEvent  # type: ignore

    @override
    @classmethod
    def player_move_type(cls) -> type[TexasHoldemMoveData]:
        return TexasHoldemMoveData

    @override
    @classmethod
    def player_view_type(cls) -> type[TexasHoldemStateView]:
        return TexasHoldemStateView

    @override
    @classmethod
    def possible_moves_type(cls) -> type[TexasHoldemPossibleMoves]:
        return TexasHoldemPossibleMoves

    @override
    @classmethod
    def agent_decision_type(cls) -> type[TexasHoldemAgentDecision]:
        return TexasHoldemAgentDecision

    @override
    @classmethod
    def reasoning_event_type(cls) -> type[BaseGameEvent]:
        return AgentReasoningEvent

    @override
    @classmethod
    def supports_spectators(cls) -> bool:
        return True

    @override
    @classmethod
    def create_reasoning_event(
        cls, turn: int, player_id: PlayerId, reasoning: AgentReasoning, tool_calls: list[ExecutedToolCall] | None = None
    ) -> BaseGameEvent:
        return AgentReasoningEvent(
            turn=turn,
            player_id=player_id,
            reasoning=reasoning,
            tool_calls=tool_calls or [],
        )

    @override
    @classmethod
    def create_chat_event(cls, turn: int, player_id: PlayerId, message: str) -> BaseGameEvent:
        return ChatMessageEvent(
            turn=turn,
            player_id=player_id,
            message=message,
        )

    @classmethod
    def default_config(cls) -> TexasHoldemConfig:
        return TexasHoldemConfig(
            small_blind=10,
            big_blind=20,
            starting_chips=1000,
            min_players=2,
            max_players=5,
        )

    @classmethod
    def config_ui_options(cls) -> dict[str, Any]:
        return {
            "small_blind": {"type": "number", "min": 1, "default": 10, "label": "Small Blind"},
            "big_blind": {"type": "number", "min": 2, "default": 20, "label": "Big Blind"},
            "starting_chips": {"type": "number", "min": 100, "step": 100, "default": 1000, "label": "Starting Chips"},
            "max_players": {"type": "number", "min": 2, "max": 9, "default": 5, "label": "Max Players"},
        }
