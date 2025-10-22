import { api } from '@/lib/api';
import { AgentId, AgentVersionId, EventId, GameId, PlayerId } from '@/types/ids';

// Enums
export enum PlayerStatusChangeReason {
  FOLDED_ACTION = "folded_action",
  ALL_IN_ACTION = "all_in_action",
  INSUFFICIENT_CHIPS = "insufficient_chips",
  GAME_ENDED = "game_ended",
  HAND_ENDED = "hand_ended",
  FORCED_ALL_IN = "forced_all_in",
}

// Agent Reasoning type - matches backend NewType("AgentReasoning", str)
// This is just a string containing the agent's reasoning text
export type AgentReasoning = string;

// ===== ENUMS =====
export enum TexasHoldemAction {
  FOLD = 'fold',
  CHECK = 'check',
  CALL = 'call',
  RAISE = 'raise',
  ALL_IN = 'all_in'
}

export enum PlayerStatus {
  ACTIVE = 'active',
  FOLDED = 'folded',
  ALL_IN = 'all_in',
  OUT = 'out'
}

export enum BettingRound {
  PREFLOP = 1,
  FLOP = 2,
  TURN = 3,
  RIVER = 4,
  SHOWDOWN = 5
}

export enum CardRank {
  TWO = '2',
  THREE = '3',
  FOUR = '4',
  FIVE = '5',
  SIX = '6',
  SEVEN = '7',
  EIGHT = '8',
  NINE = '9',
  TEN = '10',
  JACK = 'J',
  QUEEN = 'Q',
  KING = 'K',
  ACE = 'A'
}

export enum CardSuit {
  HEARTS = 'hearts',
  DIAMONDS = 'diamonds',
  CLUBS = 'clubs',
  SPADES = 'spades'
}

export enum HandRank {
  HIGH_CARD = 1,
  PAIR = 2,
  TWO_PAIR = 3,
  THREE_OF_A_KIND = 4,
  STRAIGHT = 5,
  FLUSH = 6,
  FULL_HOUSE = 7,
  FOUR_OF_A_KIND = 8,
  STRAIGHT_FLUSH = 9,
  ROYAL_FLUSH = 10
}

export enum TexasHoldemEventType {
  GAME_INITIALIZED = 'game_initialized',
  PLAYER_JOINED = 'player_joined',
  HAND_STARTED = 'hand_started',
  HOLE_CARDS_DEALT = 'hole_cards_dealt',
  PLAYER_ACTION = 'player_action',
  POT_UPDATE = 'pot_update',
  BETTING_ROUND_ADVANCED = 'betting_round_advanced',
  COMMUNITY_CARDS_DEALT = 'community_cards_dealt',
  SIDE_POTS_CREATED = 'side_pots_created',
  HAND_EVALUATED = 'hand_evaluated',
  WINNERS_ANNOUNCED = 'winners_announced',
  CHIPS_DISTRIBUTED = 'chips_distributed',
  PLAYER_STATUS_CHANGED = 'player_status_changed',
  GAME_FINISHED = 'game_finished',
  AGENT_REASONING = 'agent_reasoning'
}

// ===== BASIC TYPES =====
export interface Card {
  rank: CardRank;
  suit: CardSuit;
}

export interface SidePot {
  amount: number;
  eligible_players: string[];
}

export interface HandResult {
  rank: HandRank;
  high_cards: number[];
  description: string;
}

// ===== PLAYER TYPES =====
export interface TexasHoldemPlayerView {
  playerId: PlayerId;
  agentId: AgentId;
  chips: number;
  status: PlayerStatus;
  currentBet: number;
  totalBet: number;
  position: number;
}

export interface TexasHoldemPlayer extends TexasHoldemPlayerView {
  holeCards: Card[];
}

// ===== GAME STATE =====
export interface TexasHoldemState {
  gameType: string;
  turn: number;
  communityCards: Card[];
  pot: number;
  sidePots: SidePot[];
  currentBet: number;
  bettingRound: BettingRound;
  dealerPosition: number;
  smallBlindPosition: number;
  bigBlindPosition: number;
  actionPosition: number;
  lastRaiseAmount: number;
  lastRaisePosition: number | null;
  actedPositions: number[];
  winners: AgentId[];
  winningHands: Record<AgentId, HandResult>;
  players: TexasHoldemPlayer[];
  deck: Card[];
  currentAgentId: AgentId | null;
  currentPlayerId: PlayerId;
  isFinished: boolean;
}

export interface TexasHoldemStatePlayerView {
  gameType: string;
  communityCards: Card[];
  pot: number;
  sidePots: SidePot[];
  currentBet: number;
  bettingRound: BettingRound;
  dealerPosition: number;
  smallBlindPosition: number;
  bigBlindPosition: number;
  actionPosition: number;
  lastRaiseAmount: number;
  lastRaisePosition: number | null;
  actedPositions: number[];
  winners: AgentId[];
  winningHands: Record<AgentId, HandResult>;
  players: TexasHoldemPlayerView[];
  currentAgentId: AgentId | null;
  isFinished: boolean;
}

// ===== MOVES =====
export interface TexasHoldemMove {
  action: TexasHoldemAction;
  amount?: number;
}

export interface TexasHoldemPossibleMove {
  action: TexasHoldemAction;
  amount?: number;
  minRaiseAmount?: number;
  maxRaiseAmount?: number;
}

export interface TexasHoldemPossibleMoves {
  possibleMoves: TexasHoldemPossibleMove[];
}

// ===== EVENTS =====
export interface BaseTexasHoldemEvent {
  id: EventId;
  type: TexasHoldemEventType;
  timestamp: number;
  roundNumber: number;
}

export interface GameInitializedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.GAME_INITIALIZED;
  gameId: GameId;
}

export interface PlayerJoinedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.PLAYER_JOINED;
  playerId: PlayerId;
  agentVersionId: AgentVersionId;
  name: string;
}

export interface HandStartedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.HAND_STARTED;
  dealerPosition: number;
  smallBlindPosition: number;
  bigBlindPosition: number;
  smallBlindAmount: number;
  bigBlindAmount: number;
  smallBlindForcedAllIn: boolean;
  bigBlindForcedAllIn: boolean;
}

export interface HoleCardsDealtEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.HOLE_CARDS_DEALT;
  playerCards: Record<PlayerId, Card[]>;
}

export interface PlayerActionEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.PLAYER_ACTION;
  playerId: PlayerId;
  action: TexasHoldemAction;
  amount?: number;
  playerChipsBefore: number;
  playerChipsAfter: number;
  playerBetBefore: number;
  playerBetAfter: number;
  forcedAllIn: boolean;
  thinkingTimeMs?: number;
  statusBefore: PlayerStatus;
  statusAfter: PlayerStatus;
}

export interface PotUpdateEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.POT_UPDATE;
  potBefore: number;
  potAfter: number;
  amountAdded: number;
  currentBetBefore: number;
  currentBetAfter: number;
}

export interface BettingRoundAdvancedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.BETTING_ROUND_ADVANCED;
  fromRound: BettingRound;
  toRound: BettingRound;
  nextPlayerId?: AgentId;
}

export interface CommunityCardsDealtEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.COMMUNITY_CARDS_DEALT;
  cards: Card[];
  dealType: 'flop' | 'turn' | 'river' | 'runout';
  totalCommunityCards: number;
}

export interface SidePotsCreatedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.SIDE_POTS_CREATED;
  sidePots: SidePot[];
  mainPotAmount: number;
}

export interface HandEvaluatedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.HAND_EVALUATED;
  playerId: PlayerId;
  handResult: HandResult;
  finalHand: Card[];
}

export interface PlayerStatusChangedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.PLAYER_STATUS_CHANGED;
  playerId: PlayerId;
  fromStatus: PlayerStatus;
  toStatus: PlayerStatus;
  reason: PlayerStatusChangeReason;
}

export interface WinnersAnnouncedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.WINNERS_ANNOUNCED;
  winners: PlayerId[];
  winningHands: Record<PlayerId, HandResult>;
  uncontested: boolean;
}

export interface ChipsDistributedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.CHIPS_DISTRIBUTED;
  distributions: Array<{
    playerId: PlayerId;
    amount: number;
    source: string;
  }>;
}

export interface GameFinishedEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.GAME_FINISHED;
  finalChipCounts: Record<PlayerId, number>;
}

export interface AgentReasoningEvent extends BaseTexasHoldemEvent {
  type: TexasHoldemEventType.AGENT_REASONING;
  playerId: PlayerId;
  reasoning: AgentReasoning;
}

export type TexasHoldemEvent =
  | GameInitializedEvent
  | PlayerJoinedEvent
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
  | AgentReasoningEvent;

// ===== API REQUEST/RESPONSE TYPES =====
export interface CreateGameRequest {
  gameType: 'texas_holdem';
  config: {
    smallBlind: number;
    bigBlind: number;
    startingChips: number;
    startingChipsOverrideForTest?: Record<string, number>;
    defaultDealerPosition?: number;
    minRaise?: number;
    maxRaise?: number;
  };
  agentIds: AgentId[];
}

export interface CreatePlaygroundRequest {
  agentId: AgentVersionId;
  config: {
    smallBlind: number;
    bigBlind: number;
    startingChips: number;
    startingChipsOverrideForTest?: Record<string, number>;
    defaultDealerPosition?: number;
    minRaise?: number;
    maxRaise?: number;
  };
  numPlayers?: number;
}

export interface PokerFromStateRequest {
  agentId: AgentVersionId;
  stateView: Record<string, any>;
  config?: Record<string, any>;
  numPlayers?: number;
}

export interface CreateGameResponse {
  gameId: GameId;
  message: string;
}

export interface PlayerInfo {
  id: PlayerId;
  agentVersionId: AgentVersionId;
  name: string;
  rating?: number | null;
}

export interface GameStateResponse {
  id: GameId;
  gameType: string;
  state: TexasHoldemState;
  events: TexasHoldemEvent[];
  config: Record<string, any>;
  version: number;
  players: PlayerInfo[];
  isPlayground?: boolean;
  matchmakingStatus?: string | null;
}

export interface TurnResultResponse {
  gameId: GameId;
  newState: TexasHoldemState;
  newEvents: TexasHoldemEvent[];
  version: number;
  isFinished: boolean;
  currentPlayerId?: PlayerId;
  newCoinsBalance?: number | null; // Updated coins balance after consuming tokens (for playground moves)
}

// ===== API SERVICE =====
export class PokerApiService {
  /**
   * Transform card data from compact strings to Card objects
   */
  private static transformCardData(data: any): any {
    if (!data) return data;

    // Handle arrays of cards (could be strings or already Card objects)
    if (Array.isArray(data)) {
      return data.map(item => {
        if (typeof item === 'string') {
          return PokerUtils.compactStringToCard(item);
        }
        return item; // Already a Card object
      });
    }

    // Handle single card
    if (typeof data === 'string') {
      return PokerUtils.compactStringToCard(data);
    }

    return data; // Already a Card object or not a card
  }

  /**
   * Transform game state to convert compact string cards to Card objects
   */
  private static transformGameState(state: any): any {
    if (!state) return state;

    const transformedState = { ...state };

    // Transform community cards
    if (transformedState.communityCards) {
      transformedState.communityCards = this.transformCardData(transformedState.communityCards);
    }

    // Transform player hole cards
    if (transformedState.players && Array.isArray(transformedState.players)) {
      transformedState.players = transformedState.players.map((player: any) => {
        if (player.holeCards) {
          return {
            ...player,
            holeCards: this.transformCardData(player.holeCards)
          };
        }
        return player;
      });
    }

    return transformedState;
  }

  /**
   * Transform events to convert compact string cards to Card objects
   */
  private static transformEvents(events: any[]): any[] {
    if (!events || !Array.isArray(events)) return events;

    return events.map(event => {
      if (!event) return event;

      const transformedEvent = { ...event };

      // Transform cards in HoleCardsDealtEvent
      if (event.type === 'hole_cards_dealt' && event.playerCards) {
        transformedEvent.playerCards = Object.fromEntries(
          Object.entries(event.playerCards).map(([playerId, cards]) => [
            playerId,
            this.transformCardData(cards)
          ])
        );
      }

      // Transform cards in CommunityCardsDealtEvent
      if (event.type === 'community_cards_dealt' && event.cards) {
        transformedEvent.cards = this.transformCardData(event.cards);
      }

      return transformedEvent;
    });
  }

  /**
   * Transform complete game state response
   */
  private static transformGameStateResponse(response: any): any {
    if (!response) return response;

    const transformedResponse = { ...response };

    // Transform the main game state
    if (transformedResponse.state) {
      transformedResponse.state = this.transformGameState(transformedResponse.state);
    }

    // Transform events
    if (transformedResponse.events) {
      transformedResponse.events = this.transformEvents(transformedResponse.events);
    }

    return transformedResponse;
  }
  /**
   * Create a new Texas Hold'em game
   */
  static async createGame(request: CreateGameRequest): Promise<CreateGameResponse> {
    const response = await api.post('/api/v1/games', request);
    return response;
  }

  /**
   * Create a new Texas Hold'em playground where an agent plays against itself
   */
  static async createPlayground(request: CreatePlaygroundRequest): Promise<GameStateResponse> {
    console.log('[PokerApiService] Creating playground with request:', request);
    const response = await api.post('/api/v1/games/playground', request);
    console.log('[PokerApiService] Raw API response:', response);
    console.log('[PokerApiService] Response type:', typeof response);

    if (!response) {
      console.error('[PokerApiService] No response received from API');
      throw new Error('No response received from server');
    }

    // The fetchFromApi function returns the parsed JSON directly, not wrapped in .data
    // So response IS the actual data we need
    if (!response.id) {
      console.error('[PokerApiService] Invalid response structure - missing id:', response);
      throw new Error('Invalid response structure from server');
    }

    console.log('[PokerApiService] Successfully created playground:', response.id);
    return this.transformGameStateResponse(response);
  }

  /**
   * Get current game state with optional long polling
   */
  static async getGameState(
    gameId: GameId,
    currentVersion?: number,
    timeout?: number
  ): Promise<GameStateResponse> {
    const params = new URLSearchParams();
    if (currentVersion !== undefined) {
      params.append('current_version', currentVersion.toString());
    }
    if (timeout !== undefined) {
      params.append('timeout', timeout.toString());
    }

    const queryString = params.toString();
    const endpoint = queryString ? `/api/v1/games/${gameId}?${queryString}` : `/api/v1/games/${gameId}`;

    // Use longer timeout for long polling requests (add a generous buffer)
    const requestTimeout = timeout ? (timeout + 10) * 1000 : undefined;

    const response = await api.get(endpoint, { timeout: requestTimeout });
    return this.transformGameStateResponse(response);
  }

  /**
   * Get user's games
   */
  static async getUserGames(gameType?: string, includeFinished: boolean = false): Promise<GameStateResponse[]> {
    const params = new URLSearchParams();
    if (gameType) {
      params.append('gameType', gameType);
    }
    if (includeFinished) {
      params.append('includeFinished', 'true');
    }

    const url = `/api/v1/games${params.toString() ? '?' + params.toString() : ''}`;
    const response = await api.get(url);

    // Transform each game state response in the array
    if (Array.isArray(response)) {
      return response.map(gameState => this.transformGameStateResponse(gameState));
    }

    return response;
  }

  /**
   * Execute a turn in the game
   */
  static async executeTurn(gameId: GameId, playerId: PlayerId, moveOverride?: TexasHoldemMove, turn?: number): Promise<TurnResultResponse> {
    const requestBody = {
      playerId: playerId,
      turn: turn,
      moveOverride: moveOverride || null
    };
    // Use 5-minute timeout for agent moves to accommodate tool calls
    const response = await api.post(`/api/v1/games/${gameId}/turns`, requestBody, { timeout: 300000 });

    // Transform the response to convert compact string cards to Card objects
    const transformedResponse = { ...response };
    if (transformedResponse.newState) {
      transformedResponse.newState = this.transformGameState(transformedResponse.newState);
    }
    if (transformedResponse.newEvents) {
      transformedResponse.newEvents = this.transformEvents(transformedResponse.newEvents);
    }

    return transformedResponse;
  }

  /**
   * Create a poker playground from pasted/edited JSON state
   */
  static async createPlaygroundFromState(request: PokerFromStateRequest): Promise<GameStateResponse> {
    const response = await api.post('/api/v1/games/playground/poker/from_state', request);
    return this.transformGameStateResponse(response);
  }
}

// ===== UTILITY FUNCTIONS =====
export const PokerUtils = {
  /**
   * Get card display string
   */
  getCardString(card: Card): string {
    const suitSymbols = {
      [CardSuit.HEARTS]: '♥',
      [CardSuit.DIAMONDS]: '♦',
      [CardSuit.CLUBS]: '♣',
      [CardSuit.SPADES]: '♠'
    };
    return `${card.rank}${suitSymbols[card.suit]}`;
  },

  /**
   * Convert card to compact string format (e.g., 'Js', '10h', 'Ac')
   */
  cardToCompactString(card: Card): string {
    const suitShorthand = {
      [CardSuit.HEARTS]: 'h',
      [CardSuit.DIAMONDS]: 'd',
      [CardSuit.CLUBS]: 'c',
      [CardSuit.SPADES]: 's'
    };
    return `${card.rank}${suitShorthand[card.suit]}`;
  },

  /**
   * Parse compact string format back to Card object (e.g., 'Js' -> {rank: 'J', suit: 'spades'})
   */
  compactStringToCard(compactString: string): Card {
    if (!compactString || compactString.length < 2) {
      throw new Error(`Invalid compact card string: ${compactString}`);
    }

    const suitMap = {
      'h': CardSuit.HEARTS,
      'd': CardSuit.DIAMONDS,
      'c': CardSuit.CLUBS,
      's': CardSuit.SPADES
    };

    const suitChar = compactString.slice(-1).toLowerCase();
    const rankStr = compactString.slice(0, -1);

    if (!(suitChar in suitMap)) {
      throw new Error(`Invalid suit in compact card string: ${compactString}`);
    }

    // Validate rank
    const validRanks = Object.values(CardRank);
    if (!validRanks.includes(rankStr as CardRank)) {
      throw new Error(`Invalid rank in compact card string: ${compactString}`);
    }

    return {
      rank: rankStr as CardRank,
      suit: suitMap[suitChar as keyof typeof suitMap]
    };
  },

  /**
   * Convert array of cards to compact string format
   */
  cardsToCompactStrings(cards: Card[]): string[] {
    return cards.map(card => this.cardToCompactString(card));
  },

  /**
   * Parse array of compact strings back to Card objects
   */
  compactStringsToCards(compactStrings: string[]): Card[] {
    return compactStrings.map(str => this.compactStringToCard(str));
  },

  /**
   * Get betting round name
   */
  getBettingRoundName(round: BettingRound): string {
    switch (round) {
      case BettingRound.PREFLOP: return 'Pre-Flop';
      case BettingRound.FLOP: return 'Flop';
      case BettingRound.TURN: return 'Turn';
      case BettingRound.RIVER: return 'River';
      case BettingRound.SHOWDOWN: return 'Showdown';
      default: return 'Unknown';
    }
  },

  /**
   * Get hand rank name
   */
  getHandRankName(rank: HandRank): string {
    switch (rank) {
      case HandRank.HIGH_CARD: return 'High Card';
      case HandRank.PAIR: return 'Pair';
      case HandRank.TWO_PAIR: return 'Two Pair';
      case HandRank.THREE_OF_A_KIND: return 'Three of a Kind';
      case HandRank.STRAIGHT: return 'Straight';
      case HandRank.FLUSH: return 'Flush';
      case HandRank.FULL_HOUSE: return 'Full House';
      case HandRank.FOUR_OF_A_KIND: return 'Four of a Kind';
      case HandRank.STRAIGHT_FLUSH: return 'Straight Flush';
      case HandRank.ROYAL_FLUSH: return 'Royal Flush';
      default: return 'Unknown';
    }
  },

  /**
   * Check if player can perform action
   */
  canPlayerAct(possibleMoves: TexasHoldemPossibleMoves, action: TexasHoldemAction): boolean {
    return possibleMoves.possibleMoves.some(move => move.action === action);
  },

  /**
   * Get raise limits for player
   */
  getRaiseLimits(possibleMoves: TexasHoldemPossibleMoves): { min: number; max: number } | null {
    const raiseMove = possibleMoves.possibleMoves.find(move => move.action === TexasHoldemAction.RAISE);
    if (!raiseMove) return null;

    return {
      min: raiseMove.minRaiseAmount || 0,
      max: raiseMove.maxRaiseAmount || 0
    };
  }
};
