import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Clock, AlertCircle, Bot, User, Zap, ChevronDown, ChevronRight, Play, Shuffle, Eye, Target, DollarSign, Spade, Trophy, Brain } from 'lucide-react';
import { TexasHoldemEvent, TexasHoldemEventType, GameInitializedEvent, PlayerJoinedEvent, HandStartedEvent, HoleCardsDealtEvent, PlayerActionEvent, PotUpdateEvent, BettingRoundAdvancedEvent, CommunityCardsDealtEvent, WinnersAnnouncedEvent, ChipsDistributedEvent, AgentReasoningEvent, HandEvaluatedEvent, BettingRound, PokerUtils } from '@/services/pokerApi';
import { PlayerId } from '@/types/ids';

export interface EventLogEntry {
  id: string;
  timestamp: Date;
  type: 'error' | 'game_event' | 'agent_reasoning' | 'user_action' | 'system';
  content: string;
  details?: string;
  expandedContent?: React.ReactNode;
}

export interface GameEvent {
  id: string;
  timestamp: Date;
  type: 'error' | 'game' | 'action' | 'system';
  message: string;
  playerId?: string;
  playerName?: string;
  details?: TexasHoldemEvent;
}

interface Player {
  id: PlayerId;
  name: string;
}

interface EventLogProps {
  events: (EventLogEntry | GameEvent | TexasHoldemEvent)[];
  players?: Player[];
  className?: string;
}

const getEventIcon = (type: string) => {
  switch (type) {
    case 'error':
      return <AlertCircle className="h-4 w-4" />;
    case 'agent_reasoning':
      return <Bot className="h-4 w-4" />;
    case 'user_action':
      return <User className="h-4 w-4" />;
    case 'game_event':
      return <Zap className="h-4 w-4" />;
    case 'system':
    default:
      return <Clock className="h-4 w-4" />;
  }
};

const getTexasHoldemEventIcon = (eventType: TexasHoldemEventType) => {
  switch (eventType) {
    case TexasHoldemEventType.GAME_INITIALIZED:
      return <Play className="h-4 w-4" />;
    case TexasHoldemEventType.PLAYER_JOINED:
      return <User className="h-4 w-4" />;
    case TexasHoldemEventType.HAND_STARTED:
      return <Shuffle className="h-4 w-4" />;
    case TexasHoldemEventType.HOLE_CARDS_DEALT:
      return <Eye className="h-4 w-4" />;
    case TexasHoldemEventType.PLAYER_ACTION:
      return <Target className="h-4 w-4" />;
    case TexasHoldemEventType.POT_UPDATE:
      return <DollarSign className="h-4 w-4" />;
    case TexasHoldemEventType.BETTING_ROUND_ADVANCED:
      return <Zap className="h-4 w-4" />;
    case TexasHoldemEventType.COMMUNITY_CARDS_DEALT:
      return <Spade className="h-4 w-4" />;
    case TexasHoldemEventType.WINNERS_ANNOUNCED:
      return <Trophy className="h-4 w-4" />;
    case TexasHoldemEventType.CHIPS_DISTRIBUTED:
      return <DollarSign className="h-4 w-4" />;
    case TexasHoldemEventType.GAME_FINISHED:
      return <AlertCircle className="h-4 w-4" />;
    case TexasHoldemEventType.AGENT_REASONING:
      return <Brain className="h-4 w-4" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

const getEventColor = (type: string) => {
  switch (type) {
    case 'error':
      return 'text-red-300 bg-red-900/20 border-red-800/30 dark:text-red-300 dark:bg-red-900/20 dark:border-red-800/30';
    case 'agent_reasoning':
      return 'text-blue-300 bg-blue-900/20 border-blue-800/30 dark:text-blue-300 dark:bg-blue-900/20 dark:border-blue-800/30';
    case 'user_action':
    case 'action':
      return 'text-green-300 bg-green-900/20 border-green-800/30 dark:text-green-300 dark:bg-green-900/20 dark:border-green-800/30';
    case 'game_event':
    case 'game':
      return 'text-purple-300 bg-purple-900/20 border-purple-800/30 dark:text-purple-300 dark:bg-purple-900/20 dark:border-purple-800/30';
    case 'system':
    default:
      return 'text-gray-300 bg-gray-900/20 border-gray-800/30 dark:text-gray-300 dark:bg-gray-900/20 dark:border-gray-800/30';
  }
};

const formatTimestamp = (timestamp: Date) => {
  return timestamp.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const getPlayerNameById = (playerId: PlayerId | string | undefined, players: Player[] = []): string => {
  if (!playerId) return 'Unknown Player';
  const player = players.find(p => p.id === playerId);
  return player?.name || `Player ${String(playerId).slice(-8)}`;
};

const generateExpandedContent = (event: TexasHoldemEvent, players: Player[] = []): React.ReactNode => {
  switch (event.type) {
    case TexasHoldemEventType.PLAYER_ACTION: {
      const actionEvent = event as PlayerActionEvent;
      const showStatusChange = actionEvent.action === 'fold' && actionEvent.statusBefore !== actionEvent.statusAfter;

      return (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Chips</div>
              <div>Before: {actionEvent.playerChipsBefore?.toLocaleString() || 'N/A'}</div>
              <div>After: {actionEvent.playerChipsAfter?.toLocaleString() || 'N/A'}</div>
            </div>
            <div>
              <div className="font-medium text-blue-200">Bet</div>
              <div>Before: {actionEvent.playerBetBefore?.toLocaleString() || 'N/A'}</div>
              <div>After: {actionEvent.playerBetAfter?.toLocaleString() || 'N/A'}</div>
            </div>
          </div>
          {actionEvent.amount && (
            <div><span className="font-medium text-blue-200">Amount:</span> {actionEvent.amount.toLocaleString()}</div>
          )}
          {showStatusChange && (
            <div><span className="font-medium text-blue-200">Status:</span> {actionEvent.statusBefore} → {actionEvent.statusAfter}</div>
          )}
          {actionEvent.forcedAllIn && (
            <div className="text-yellow-300">⚠️ Forced all-in</div>
          )}
        </div>
      );
    }

    case TexasHoldemEventType.POT_UPDATE: {
      const potEvent = event as PotUpdateEvent;
      return (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Pot</div>
              <div>Before: {potEvent.potBefore?.toLocaleString() || 'N/A'}</div>
              <div>After: {potEvent.potAfter?.toLocaleString() || 'N/A'}</div>
            </div>
            <div>
              <div className="font-medium text-blue-200">Current Bet</div>
              <div>Before: {potEvent.currentBetBefore?.toLocaleString() || 'N/A'}</div>
              <div>After: {potEvent.currentBetAfter?.toLocaleString() || 'N/A'}</div>
            </div>
          </div>
          <div><span className="font-medium text-blue-200">Amount Added:</span> {potEvent.amountAdded?.toLocaleString() || 'N/A'}</div>
        </div>
      );
    }

    case TexasHoldemEventType.COMMUNITY_CARDS_DEALT: {
      const cardsEvent = event as CommunityCardsDealtEvent;
      const formattedCards = cardsEvent.cards.map(card => PokerUtils.cardToCompactString(card)).join(', ');

      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Deal Type:</span> {cardsEvent.dealType}</div>
          <div><span className="font-medium text-blue-200">Cards:</span> {formattedCards}</div>
          <div><span className="font-medium text-blue-200">Total Community Cards:</span> {cardsEvent.totalCommunityCards}</div>
        </div>
      );
    }

    case TexasHoldemEventType.HOLE_CARDS_DEALT: {
      const holeCardsEvent = event as HoleCardsDealtEvent;
      return (
        <div className="space-y-2 text-sm">
          <div className="font-medium text-blue-200">Player Cards:</div>
          {Object.entries(holeCardsEvent.playerCards).map(([playerId, cards]) => {
            const formattedCards = cards.map(card => PokerUtils.cardToCompactString(card)).join(', ');
            return (
              <div key={playerId} className="ml-2">
                <span className="text-gray-300">{getPlayerNameById(playerId, players)}:</span> {formattedCards}
              </div>
            );
          })}
        </div>
      );
    }

    case TexasHoldemEventType.HAND_STARTED: {
      const handEvent = event as HandStartedEvent;
      return (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Blinds</div>
              <div>Small: {handEvent.smallBlindAmount} (Pos: {handEvent.smallBlindPosition})</div>
              <div>Big: {handEvent.bigBlindAmount} (Pos: {handEvent.bigBlindPosition})</div>
            </div>
            <div>
              <div className="font-medium text-blue-200">Positions</div>
              <div>Dealer: {handEvent.dealerPosition}</div>
            </div>
          </div>
          {(handEvent.smallBlindForcedAllIn || handEvent.bigBlindForcedAllIn) && (
            <div className="text-yellow-300">⚠️ Forced all-in blinds</div>
          )}
        </div>
      );
    }

    case TexasHoldemEventType.BETTING_ROUND_ADVANCED: {
      const roundEvent = event as BettingRoundAdvancedEvent;
      const fromRoundName = getPokerRoundName(roundEvent.fromRound);
      const toRoundName = getPokerRoundName(roundEvent.toRound);

      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Round:</span> {fromRoundName} → {toRoundName}</div>
          {roundEvent.nextPlayerId && (
            <div><span className="font-medium text-blue-200">Next Player:</span> {getPlayerNameById(roundEvent.nextPlayerId, players)}</div>
          )}
        </div>
      );
    }

    case TexasHoldemEventType.GAME_INITIALIZED: {
      const gameEvent = event as GameInitializedEvent;
      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Game ID:</span> {gameEvent.gameId.slice(-8)}</div>
          <div><span className="font-medium text-blue-200">Game initialized</span></div>
        </div>
      );
    }

    case TexasHoldemEventType.AGENT_REASONING: {
      const reasoningEvent = event as AgentReasoningEvent;
      return (
        <div className="space-y-2">
          <div><span className="font-medium text-blue-200">Player:</span> {getPlayerNameById(reasoningEvent.playerId, players)}</div>
          <div className="text-gray-300 italic">
            {reasoningEvent.reasoning}
          </div>
        </div>
      );
    }

    case TexasHoldemEventType.WINNERS_ANNOUNCED: {
      const winnersEvent = event as WinnersAnnouncedEvent;
      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Winners:</span> {(winnersEvent.winners || []).map(id => getPlayerNameById(id, players)).join(', ')}</div>
          <div><span className="font-medium text-blue-200">Uncontested:</span> {winnersEvent.uncontested ? 'Yes' : 'No'}</div>
          {Object.entries(winnersEvent.winningHands || {}).map(([playerId, hand]) => (
            <div key={playerId} className="ml-2">
              {getPlayerNameById(playerId, players)}: {hand.description}
            </div>
          ))}
        </div>
      );
    }

    case TexasHoldemEventType.CHIPS_DISTRIBUTED: {
      const chipsEvent = event as ChipsDistributedEvent;
      return (
        <div className="space-y-2 text-sm">
          <div className="font-medium text-blue-200">Distributions:</div>
          {(chipsEvent.distributions || []).map((dist, index) => (
            <div key={index} className="ml-2">
              {getPlayerNameById(dist.playerId, players)}: +${dist.amount} from {dist.source}
            </div>
          ))}
        </div>
      );
    }

    default:
      return (
        <div className="space-y-1 text-sm">
          <pre className="text-xs">{JSON.stringify(event, null, 2)}</pre>
        </div>
      );
  }
};

// Helper function to map betting rounds to poker round names
const getPokerRoundName = (round: BettingRound): string => {
  switch (round) {
    case BettingRound.PREFLOP: return 'Pre-flop';
    case BettingRound.FLOP: return 'Flop';
    case BettingRound.TURN: return 'Turn';
    case BettingRound.RIVER: return 'River';
    case BettingRound.SHOWDOWN: return 'Showdown';
    default: return String(round);
  }
};

const formatEventMessage = (event: EventLogEntry | GameEvent | TexasHoldemEvent, players: Player[] = []): string => {
  // If it's already a formatted message, return as-is
  if ('message' in event) {
    return event.message;
  }

  // Handle EventLogEntry
  if ('content' in event) {
    return event.content;
  }

  // Handle TexasHoldemEvent types with proper typing
  const texasEvent = event as TexasHoldemEvent;
  switch (texasEvent.type) {
    case TexasHoldemEventType.GAME_INITIALIZED: {
      return "Game initialized";
    }

    case TexasHoldemEventType.PLAYER_JOINED: {
      const playerEvent = texasEvent as PlayerJoinedEvent;
      return `${playerEvent.name} joined the game`;
    }

    case TexasHoldemEventType.HAND_STARTED: {
      const handEvent = texasEvent as HandStartedEvent;
      return `New hand started (Round ${handEvent.roundNumber})`;
    }

    case TexasHoldemEventType.HOLE_CARDS_DEALT:
      return 'Hole cards dealt';

    case TexasHoldemEventType.BETTING_ROUND_ADVANCED: {
      const roundEvent = texasEvent as BettingRoundAdvancedEvent;
      const fromRound = getPokerRoundName(roundEvent.fromRound);
      const toRound = getPokerRoundName(roundEvent.toRound);
      return `Betting round advanced: ${fromRound} → ${toRound}`;
    }

    case TexasHoldemEventType.PLAYER_ACTION: {
      const actionEvent = texasEvent as PlayerActionEvent;
      const playerName = getPlayerNameById(actionEvent.playerId, players);

      switch (actionEvent.action) {
        case 'fold':
          return `${playerName} folds`;
        case 'check':
          return `${playerName} checks`;
        case 'call':
          return `${playerName} calls`;
        case 'raise':
          return `${playerName} raises${actionEvent.amount ? ` to $${actionEvent.amount}` : ''}`;
        case 'all_in':
          return `${playerName} goes all-in${actionEvent.amount ? ` with $${actionEvent.amount}` : ''}`;
        default:
          return `${playerName} ${actionEvent.action}`;
      }
    }

    case TexasHoldemEventType.COMMUNITY_CARDS_DEALT: {
      const cardsEvent = texasEvent as CommunityCardsDealtEvent;
      const cardStrings = cardsEvent.cards?.map(card => PokerUtils.cardToCompactString(card)).join(', ') || '';

      switch (cardsEvent.dealType) {
        case 'flop':
          return `Flop dealt: ${cardStrings}`;
        case 'turn':
          return `Turn dealt: ${cardStrings}`;
        case 'river':
          return `River dealt: ${cardStrings}`;
        default:
          return `Community cards dealt: ${cardStrings}`;
      }
    }

    case TexasHoldemEventType.POT_UPDATE: {
      const potEvent = texasEvent as PotUpdateEvent;
      return `Pot updated to $${potEvent.potAfter}`;
    }

    case TexasHoldemEventType.WINNERS_ANNOUNCED: {
      const winnersEvent = texasEvent as WinnersAnnouncedEvent;
      if (winnersEvent.winners?.length === 1) {
        const winnerId = winnersEvent.winners[0];
        return `${getPlayerNameById(winnerId, players)} wins the hand`;
      } else if (winnersEvent.winners?.length > 1) {
        return `${winnersEvent.winners.length} players split the pot`;
      }
      return 'Hand completed';
    }

    case TexasHoldemEventType.CHIPS_DISTRIBUTED: {
      const chipsEvent = texasEvent as ChipsDistributedEvent;
      const totalDistributed = chipsEvent.distributions?.reduce((sum, dist) => sum + dist.amount, 0) || 0;
      return `$${totalDistributed} distributed to winners`;
    }

    case TexasHoldemEventType.GAME_FINISHED:
      return 'Game finished';

    case TexasHoldemEventType.AGENT_REASONING: {
      const reasoningEvent = texasEvent as AgentReasoningEvent;
      return `${getPlayerNameById(reasoningEvent.playerId, players)} reasoning`;
    }

    case TexasHoldemEventType.SIDE_POTS_CREATED:
      return 'Side pots created';

    case TexasHoldemEventType.HAND_EVALUATED: {
      const handEvent = texasEvent as HandEvaluatedEvent;
      const finalHandStr = handEvent.finalHand?.map(card => PokerUtils.cardToCompactString(card)).join(', ') || '';
      return `${getPlayerNameById(handEvent.playerId, players)} evaluated hand: ${handEvent.handResult?.description || 'Unknown'} (${finalHandStr})`;
    }

    case TexasHoldemEventType.PLAYER_STATUS_CHANGED:
      return 'Player status changed';

    default:
      return `Unknown event: ${(texasEvent as any).type}`;
  }
};

export const EventLog: React.FC<EventLogProps> = ({ events, players = [], className = '' }) => {
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  const toggleEventExpansion = (eventId: string) => {
    setExpandedEvents(prev => ({
      ...prev,
      [eventId]: !prev[eventId]
    }));
  };

  // Convert all event types to EventLogEntry format and sort by timestamp (newest first)
  const normalizedEvents = events.map((event, index) => {
    if ('message' in event) {
      // This is a GameEvent, convert to EventLogEntry format
      return {
        id: event.id,
        timestamp: event.timestamp,
        type: event.type === 'game' ? 'game_event' as const :
              event.type === 'action' ? 'user_action' as const :
              event.type as 'error' | 'system',
        content: event.message,
        details: event.details ? JSON.stringify(event.details) : undefined
      };
    } else if ('type' in event && typeof event.type === 'string' && !('content' in event)) {
      // This is a TexasHoldemEvent, convert to EventLogEntry format
      const texasEvent = event as TexasHoldemEvent;
      return {
        id: `texas-${texasEvent.type}-${texasEvent.timestamp}-${index}`,
        timestamp: new Date(texasEvent.timestamp * 1000), // Convert Unix timestamp to milliseconds
        type: texasEvent.type === TexasHoldemEventType.AGENT_REASONING ? 'agent_reasoning' as const : 'game_event' as const,
        content: formatEventMessage(event, players),
        details: JSON.stringify(event),
        expandedContent: generateExpandedContent(texasEvent, players)
      } as EventLogEntry;
    }
    // This is already an EventLogEntry
    return event as EventLogEntry;
  });

  const sortedEvents = [...normalizedEvents].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

  return (
    <Card className={`w-full max-w-md h-full flex flex-col rounded-xl mb-4 ${className}`} data-testid="event-log-sidebar">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Event Log
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <div className="h-full pl-6 pr-4 py-2 overflow-y-auto scrollbar-visible">
          <div className="space-y-4 pb-4">
            {sortedEvents.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No events yet</p>
                <p className="text-sm">Events will appear here as they occur</p>
              </div>
            ) : (
              sortedEvents.map((event) => {
                const isExpanded = expandedEvents[event.id] || false;
                const hasExpandableContent = !!event.expandedContent;
                const isTexasHoldemEvent = event.details && event.details.startsWith('{"type"');
                const icon = isTexasHoldemEvent ? 
                  getTexasHoldemEventIcon((JSON.parse(event.details!) as TexasHoldemEvent).type) : 
                  getEventIcon(event.type);

                return (
                  <Card
                    key={event.id}
                    className={`p-4 transition-all duration-200 relative ${
                      getEventColor(event.type)
                    } ${
                      event.type === 'agent_reasoning' ? 'border-l-4 border-l-blue-500' : ''
                    } ${
                      hasExpandableContent
                        ? 'cursor-pointer hover:bg-opacity-80 hover:shadow-md border-2 border-transparent hover:border-gray-600/30'
                        : ''
                    }`}
                    onClick={() => hasExpandableContent && toggleEventExpansion(event.id)}
                    data-testid="event-entry"
                    role={hasExpandableContent ? "button" : undefined}
                    tabIndex={hasExpandableContent ? 0 : undefined}
                    onKeyDown={(e) => {
                      if (hasExpandableContent && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        toggleEventExpansion(event.id);
                      }
                    }}
                    aria-expanded={hasExpandableContent ? isExpanded : undefined}
                    aria-label={hasExpandableContent ? `Event ${sortedEvents.length - sortedEvents.indexOf(event)}: ${isExpanded ? 'Collapse' : 'Expand'} event details` : `Event ${sortedEvents.length - sortedEvents.indexOf(event)}`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex-shrink-0 w-5 h-5 bg-gray-700/50 border border-gray-600/30 rounded-full flex items-center justify-center">
                          <span className="text-[10px] font-mono text-gray-300 font-medium">
                            {sortedEvents.length - sortedEvents.indexOf(event)}
                          </span>
                        </div>
                        <div className="flex-shrink-0">
                          {icon}
                        </div>
                        <Badge
                          variant="outline"
                          className={`text-xs capitalize px-2.5 py-1 flex-shrink-0 ${
                            event.type === 'agent_reasoning'
                              ? 'bg-blue-900/40 border-blue-600/50 text-blue-200'
                              : ''
                          }`}
                        >
                          {event.type === 'agent_reasoning' ? 'Agent' : event.type === 'game_event' ? 'Game' : event.type.replace('_', ' ')}
                        </Badge>
                        <div className="flex-1 min-w-0"></div>
                        <span
                          className="text-xs font-mono opacity-75 flex-shrink-0"
                          data-testid="event-timestamp"
                        >
                          {formatTimestamp(event.timestamp)}
                        </span>
                        
                        {hasExpandableContent && (
                          <div className="flex-shrink-0 w-6 flex items-center justify-center transition-transform duration-200">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4 opacity-70" />
                            ) : (
                              <ChevronRight className="h-4 w-4 opacity-70" />
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="w-full">
                        <div className="text-sm font-medium leading-relaxed break-words" data-testid="event-content">
                          {event.content}
                        </div>
                      </div>
                      
                      {hasExpandableContent && isExpanded && (
                        <div className="w-full">
                          <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-600/20 animate-in slide-in-from-top-2 duration-200">
                            {event.expandedContent}
                          </div>
                        </div>
                      )}
                    </div>
                  </Card>
                );
              })
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};