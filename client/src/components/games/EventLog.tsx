import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Clock, AlertCircle, Bot, User, Zap, ChevronDown, ChevronRight, Brain } from 'lucide-react';
import { PokerUtils, TexasHoldemEvent } from '@/services/pokerApi';

export interface EventLogEntry {
  id: string;
  timestamp: Date;
  type: 'error' | 'game_event' | 'agent_reasoning' | 'user_action' | 'system' | 'move_analysis';
  content: string;
  details?: string | any;
  expandedContent?: React.ReactNode; // Rich content to show when expanded
}

// GameEvent interface to match what PokerGame expects
export interface GameEvent {
  id: string;
  timestamp: Date;
  type: 'error' | 'game' | 'action' | 'system';
  message: string;
  playerId?: string;
  playerName?: string;
  details?: any;
}

interface EventLogProps {
  events: (EventLogEntry | GameEvent | TexasHoldemEvent)[];
  className?: string;
  /**
   * Maximum height for the EventLog card. When content exceeds this height, the inner list scrolls.
   * Accepts a Tailwind-compatible string (e.g., '70vh') or a number of pixels.
   */
  maxHeight?: string | number;
  /**
   * When true, removes the default bottom margin to allow exact height alignment in tight layouts.
   */
  noMargin?: boolean;
  /**
   * When true, renders without the Card wrapper (for use inside modals/dialogs)
   */
  noCard?: boolean;
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
    case 'move_analysis':
      return <Brain className="h-4 w-4" />;
    case 'system':
    default:
      return <Clock className="h-4 w-4" />;
  }
};

const getEventColor = (type: string) => {
  // Use theme tokens instead of hard-coded colors for consistency across light/dark modes
  switch (type) {
    case 'error':
      return 'text-destructive bg-destructive/10 border-destructive/30';
    case 'agent_reasoning':
      return 'text-primary bg-primary/10 border-primary/30';
    case 'user_action':
    case 'action':
      return 'text-brand-mint bg-brand-mint/10 border-brand-mint/30';
    case 'game_event':
    case 'game':
      return 'text-brand-purple bg-brand-purple/10 border-brand-purple/30';
    case 'move_analysis':
      return 'text-brand-orange bg-brand-orange/10 border-brand-orange/30';
    case 'system':
    default:
      return 'text-muted-foreground bg-muted/10 border-border/30';
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

const generateExpandedContent = (event: any): React.ReactNode => {
  if (!event || typeof event !== 'object') return null;

  const eventType = event.type;

  switch (eventType) {
    case 'player_action':
      // Only show relevant information, avoid status transitions for raises
      const showStatusChange = event.action === 'fold' && event.status_before !== event.status_after;

      return (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Chips</div>
              <div>Before: {event.player_chips_before?.toLocaleString() || 'N/A'}</div>
              <div>After: {event.player_chips_after?.toLocaleString() || 'N/A'}</div>
            </div>
            <div>
              <div className="font-medium text-blue-200">Bet</div>
              <div>Before: {event.player_bet_before?.toLocaleString() || 'N/A'}</div>
              <div>After: {event.player_bet_after?.toLocaleString() || 'N/A'}</div>
            </div>
          </div>
          {event.amount && (
            <div><span className="font-medium text-blue-200">Amount:</span> {event.amount.toLocaleString()}</div>
          )}
          {showStatusChange && (
            <div><span className="font-medium text-blue-200">Status:</span> {event.status_before} → {event.status_after}</div>
          )}
          {event.forced_all_in && (
            <div className="text-yellow-300">⚠️ Forced all-in</div>
          )}
        </div>
      );

    case 'pot_update':
      return (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Pot</div>
              <div>Before: {event.pot_before?.toLocaleString() || 'N/A'}</div>
              <div>After: {event.pot_after?.toLocaleString() || 'N/A'}</div>
            </div>
            <div>
              <div className="font-medium text-blue-200">Current Bet</div>
              <div>Before: {event.current_bet_before?.toLocaleString() || 'N/A'}</div>
              <div>After: {event.current_bet_after?.toLocaleString() || 'N/A'}</div>
            </div>
          </div>
          <div><span className="font-medium text-blue-200">Amount Added:</span> {event.amount_added?.toLocaleString() || 'N/A'}</div>
        </div>
      );

    case 'community_cards_dealt':
      const communityCards = event.cards || [];
      const formattedCommunityCards = communityCards.map((card: any) => {
        if (typeof card === 'string') {
          return card;
        }
        return PokerUtils.cardToCompactString(card);
      }).join(', ');

      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Deal Type:</span> {event.deal_type}</div>
          <div><span className="font-medium text-blue-200">Cards:</span> {formattedCommunityCards || 'N/A'}</div>
          <div><span className="font-medium text-blue-200">Total Community Cards:</span> {event.total_community_cards || 'N/A'}</div>
        </div>
      );

    case 'hole_cards_dealt':
      return (
        <div className="space-y-2 text-sm">
          <div className="font-medium text-blue-200">Player Cards:</div>
          {event.player_cards && Object.entries(event.player_cards).map(([playerId, cards]: [string, any]) => {
            const formattedCards = Array.isArray(cards) ? cards.map((card: any) => {
              if (typeof card === 'string') {
                return card;
              }
              return PokerUtils.cardToCompactString(card);
            }).join(', ') : 'N/A';

            return (
              <div key={playerId} className="ml-2">
                <span className="text-gray-300">Player {playerId.slice(-8)}:</span> {formattedCards}
              </div>
            );
          })}
        </div>
      );

    case 'hand_started':
      return (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Blinds</div>
              <div>Small: {event.small_blind_amount} (Pos: {event.small_blind_position})</div>
              <div>Big: {event.big_blind_amount} (Pos: {event.big_blind_position})</div>
            </div>
            <div>
              <div className="font-medium text-blue-200">Positions</div>
              <div>Dealer: {event.dealer_position}</div>
            </div>
          </div>
          {(event.small_blind_forced_all_in || event.big_blind_forced_all_in) && (
            <div className="text-yellow-300">⚠️ Forced all-in blinds</div>
          )}
        </div>
      );

    case 'betting_round_advanced':
      const fromRoundName = getPokerRoundName(event.from_round || 1);
      const toRoundName = getPokerRoundName(event.to_round || 2);

      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Round:</span> {fromRoundName} → {toRoundName}</div>
          {event.next_player_id && (
            <div><span className="font-medium text-blue-200">Next Player:</span> {event.next_player_id.slice(-8)}</div>
          )}
        </div>
      );

    case 'game_initialized':
      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Game ID:</span> {event.game_id?.slice(-8) || 'N/A'}</div>
          <div><span className="font-medium text-blue-200">Players:</span> {event.agent_ids?.length || 0}</div>
          {event.starting_chips && (
            <div>
              <div className="font-medium text-blue-200">Starting Chips:</div>
              {Object.entries(event.starting_chips).map(([playerId, chips]: [string, any]) => (
                <div key={playerId} className="ml-2">
                  Player {playerId.slice(-8)}: {chips?.toLocaleString()}
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case 'agent_reasoning':
      return (
        <div className="space-y-3 text-sm">
          <div><span className="font-medium text-blue-200">Agent:</span> {event.agent_name}</div>
          <div><span className="font-medium text-blue-200">Player:</span> {event.player_id?.slice(-8)}</div>
          <div className="text-blue-100 whitespace-pre-wrap leading-relaxed">
            {event.reasoning}
          </div>
        </div>
      );

    case 'Move Analysis':
      const getMoveQualityBadge = () => {
        if (event.is_brilliant) return <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/40">✨ Brilliant</Badge>;
        if (event.is_good) return <Badge className="bg-green-500/20 text-green-300 border-green-500/40">✓ Good</Badge>;
        if (event.is_inaccuracy) return <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/40">~ Inaccuracy</Badge>;
        if (event.is_mistake) return <Badge className="bg-orange-500/20 text-orange-300 border-orange-500/40">? Mistake</Badge>;
        if (event.is_blunder) return <Badge className="bg-red-500/20 text-red-300 border-red-500/40">?? Blunder</Badge>;
        return null;
      };

      const formatEvaluation = (cp: number | null, mate: number | null) => {
        if (mate !== null && mate !== undefined) {
          return mate > 0 ? `M${mate}` : `M${Math.abs(mate)}`;
        }
        if (cp !== null && cp !== undefined) {
          const pawns = (cp / 100).toFixed(2);
          return cp >= 0 ? `+${pawns}` : pawns;
        }
        return 'N/A';
      };

      return (
        <div className="space-y-3 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-medium text-blue-200">Move Quality:</span>
            {getMoveQualityBadge()}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium text-blue-200">Evaluation</div>
              <div className="text-lg font-mono">{formatEvaluation(event.evaluation_cp, event.evaluation_mate)}</div>
            </div>
            {event.best_move_san && event.best_move_san !== event.move_san && (
              <div>
                <div className="font-medium text-blue-200">Best Move</div>
                <div className="text-lg font-mono">{event.best_move_san}</div>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-border/40">
            <div className="font-medium text-blue-200 mb-2">Analysis</div>
            <div className="text-blue-100 leading-relaxed">
              {event.narrative}
            </div>
          </div>
        </div>
      );

    case 'agent_forfeit':
      return (
        <div className="space-y-2 text-sm">
          <div><span className="font-medium text-blue-200">Agent:</span> Player {event.player_id?.slice(-8)}</div>
          <div><span className="font-medium text-blue-200">Reason:</span> {event.reason || 'Failed to move within attempt limit'}</div>
        </div>
      );

    default:
      // For unknown event types, show all available data
      const filteredData = Object.entries(event)
        .filter(([key]) => !['timestamp', 'type'].includes(key))
        .slice(0, 10); // Limit to prevent overwhelming display

      if (filteredData.length === 0) return null;

      return (
        <div className="space-y-1 text-sm">
          {filteredData.map(([key, value]) => (
            <div key={key}>
              <span className="font-medium text-blue-200">{key.replace(/_/g, ' ')}:</span>{' '}
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </div>
          ))}
        </div>
      );
  }
};

// Helper function to map numeric rounds to poker round names
const getPokerRoundName = (round: number): string => {
  switch (round) {
    case 1: return 'Pre-flop';
    case 2: return 'Flop';
    case 3: return 'Turn';
    case 4: return 'River';
    default: return `Round ${round}`;
  }
};

const formatEventMessage = (event: EventLogEntry | GameEvent | TexasHoldemEvent): string => {
  // If it's already a formatted message, return as-is
  if ('message' in event) {
    return event.message;
  }

  // Handle EventLogEntry
  if ('content' in event) {
    return event.content;
  }

  // Handle TexasHoldemEvent types
  if ('type' in event && typeof event.type === 'string') {
    const texasEvent = event as any;
    switch (texasEvent.type) {
      case 'game_initialized':
        const playerCount = texasEvent.agent_ids?.length || 0;
        return `Game started with ${playerCount} players`;

      case 'hand_started':
        return `New hand started (Round ${texasEvent.turn || 1})`;

      case 'hole_cards_dealt':
        return `Hole cards dealt`;

      case 'betting_round_advanced':
        const fromRound = getPokerRoundName(texasEvent.from_round || 1);
        const toRound = getPokerRoundName(texasEvent.to_round || 2);
        return `Betting round advanced: ${fromRound} → ${toRound}`;

      case 'player_action':
        const action = texasEvent.action;
        const playerName = `Player ${texasEvent.player_id?.slice(-8) || 'Unknown'}`;

        switch (action) {
          case 'fold':
            return `${playerName} folds`;
          case 'check':
            return `${playerName} checks`;
          case 'call':
            return `${playerName} calls`;
          case 'raise':
            return `${playerName} raises${texasEvent.amount ? ` to $${texasEvent.amount}` : ''}`;
          case 'all_in':
            return `${playerName} goes all-in${texasEvent.amount ? ` with $${texasEvent.amount}` : ''}`;
          default:
            return `${playerName} ${action}`;
        }

      case 'community_cards_dealt':
        const cards = texasEvent.cards || [];
        const cardStrings = cards.map((card: any) => {
          if (typeof card === 'string') {
            return card;
          }
          return PokerUtils.cardToCompactString(card);
        }).join(', ');

        switch (texasEvent.deal_type) {
          case 'flop':
            return `Flop dealt: ${cardStrings}`;
          case 'turn':
            return `Turn dealt: ${cardStrings}`;
          case 'river':
            return `River dealt: ${cardStrings}`;
          default:
            return `Community cards dealt: ${cardStrings}`;
        }

      case 'winners_announced':
        const winners = texasEvent.winners || [];
        if (winners.length === 1) {
          const winnerId = winners[0];
          return `Player ${winnerId.slice(-8)} wins the hand`;
        } else if (winners.length > 1) {
          return `${winners.length} players split the pot`;
        }
        return 'Hand completed';

      case 'chips_distributed':
        const totalDistributed = texasEvent.distributions?.reduce((sum: number, dist: any) => sum + (dist.amount || 0), 0) || 0;
        return `$${totalDistributed} distributed to winners`;

      case 'game_finished':
        return 'Game finished';

      case 'agent_reasoning':
        const agentName = texasEvent.agent_name || 'Agent';
        const reasoningText = texasEvent.reasoning?.trim() || '';
        return reasoningText ? `${agentName}: ${reasoningText}` : `${agentName} shared their reasoning`;

      case 'Move Analysis':
        const moveQuality = texasEvent.is_brilliant ? '✨ Brilliant' :
                           texasEvent.is_good ? '✓ Good' :
                           texasEvent.is_inaccuracy ? '~ Inaccuracy' :
                           texasEvent.is_mistake ? '? Mistake' :
                           texasEvent.is_blunder ? '?? Blunder' : '';
        return `${texasEvent.move_san}${moveQuality ? ` ${moveQuality}` : ' analyzed'}`;

      case 'agent_forfeit':
        const forfeitPlayerName = `Player ${texasEvent.player_id?.slice(-8) || 'Unknown'}`;
        const forfeitReason = texasEvent.reason || 'Failed to move within attempt limit';
        return `${forfeitPlayerName} forfeits: ${forfeitReason}`;

      default:
        // Improve default event naming
        const eventName = texasEvent.type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
        return eventName;
    }
  }

  // Handle raw event data with details (legacy format)
  const details = (event as any).details || event;
  const eventType = details.type || (event as any).type;

  if (!eventType) {
    return 'Unknown event';
  }

  switch (eventType) {
    case 'game_initialized':
      const playerCount = details.agent_ids?.length || 0;
      return `Game started with ${playerCount} players`;

    case 'hand_started':
      const round = details.turn || 1;
      return `New hand started (Round ${round})`;

    case 'hole_cards_dealt':
      const playerCards = details.player_cards || {};
      const playersWithCards = Object.keys(playerCards).length;
      return `Hole cards dealt to ${playersWithCards} players`;

    case 'player_action':
      const action = details.action;
      const playerName = (event as any).playerName || `Player ${details.player_id?.slice(-8) || 'Unknown'}`;

      switch (action) {
        case 'fold':
          return `${playerName} folds`;
        case 'check':
          return `${playerName} checks`;
        case 'call':
          return `${playerName} calls`;
        case 'raise':
          return `${playerName} raises${details.amount ? ` to $${details.amount}` : ''}`;
        case 'all_in':
          return `${playerName} goes all-in${details.amount ? ` with $${details.amount}` : ''}`;
        default:
          return `${playerName} ${action}`;
      }

    case 'community_cards_dealt':
      const cards = details.cards || [];
      const cardStrings = cards.map((card: any) => {
        if (typeof card === 'string') {
          return card;
        }
        return PokerUtils.cardToCompactString(card);
      }).join(', ');

      switch (details.deal_type) {
        case 'flop':
          return `Flop dealt: ${cardStrings}`;
        case 'turn':
          return `Turn dealt: ${cardStrings}`;
        case 'river':
          return `River dealt: ${cardStrings}`;
        default:
          return `Community cards dealt: ${cardStrings}`;
      }

    case 'betting_round_advanced':
      const fromRound = getPokerRoundName(details.from_round || 1);
      const toRound = getPokerRoundName(details.to_round || 2);
      return `Betting round advanced: ${fromRound} → ${toRound}`;

    case 'pot_update':
      const potAfter = details.pot_after || 0;
      return `Pot updated to $${potAfter}`;

    case 'winners_announced':
      const winners = details.winners || [];
      const winningHands = details.winning_hands || {};
      if (winners.length === 1) {
        const winnerId = winners[0];
        const winningHand = winningHands[winnerId];
        if (winningHand) {
          return `${winnerId.slice(-8)} wins with ${winningHand.description}`;
        }
        return `${winnerId.slice(-8)} wins the hand`;
      } else if (winners.length > 1) {
        return `${winners.length} players split the pot`;
      }
      return 'Hand completed';

    case 'chips_distributed':
      const totalDistributed = details.distributions?.reduce((sum: number, dist: any) => sum + (dist.amount || 0), 0) || 0;
      return `$${totalDistributed} distributed to winners`;

    case 'game_finished':
      return 'Game finished';

    default:
      const eventName = eventType.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
      return eventName;
  }

};

export const EventLog: React.FC<EventLogProps> = ({ events, className = '', maxHeight = '70vh', noMargin = false, noCard = false }) => {
  // State management for tracking expanded/collapsed state of events
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  // Toggle function for expanding/collapsing event content
  const toggleEventExpansion = (eventId: string) => {
    setExpandedEvents(prev => ({
      ...prev,
      [eventId]: !prev[eventId]
    }));
  };
  // Helper function to ensure timestamp is a Date object
  const ensureDate = (timestamp: any): Date => {
    if (timestamp instanceof Date) {
      return timestamp;
    }
    if (typeof timestamp === 'number') {
      // If it's a Unix timestamp (seconds), convert to milliseconds
      return new Date(timestamp < 10000000000 ? timestamp * 1000 : timestamp);
    }
    if (typeof timestamp === 'string') {
      return new Date(timestamp);
    }
    return new Date();
  };

  // Convert all event types to EventLogEntry format and sort by timestamp (newest first)
  const normalizedEvents = events.map((event, index) => {
    if ('message' in event) {
      // This is a GameEvent, convert to EventLogEntry format
      return {
        id: event.id,
        timestamp: ensureDate(event.timestamp),
        type: event.type === 'game' ? 'game_event' as const :
              event.type === 'action' ? 'user_action' as const :
              event.type as 'error' | 'system',
        content: event.message,
        details: event.details ? JSON.stringify(event.details) : undefined
      };
    } else if ('type' in event && typeof event.type === 'string' && !('content' in event)) {
      // This is a TexasHoldemEvent or ChessEvent, convert to EventLogEntry format
      const texasEvent = event as any;

      // Determine event type
      let eventType: EventLogEntry['type'] = 'game_event';
      if (texasEvent.type === 'agent_reasoning') {
        eventType = 'agent_reasoning';
      } else if (texasEvent.event === 'Move Analysis') {
        eventType = 'move_analysis';
      }

      return {
        id: texasEvent.id || `texas-${texasEvent.type}-${texasEvent.timestamp}-${index}`, // Use proper EventId from backend
        timestamp: ensureDate(texasEvent.timestamp), // Convert Unix timestamp to Date
        type: eventType,
        content: formatEventMessage(event),
        details: JSON.stringify(event),
        expandedContent: generateExpandedContent(texasEvent)
       } as EventLogEntry;
    }
    // This is already an EventLogEntry - ensure timestamp is a Date
    return {
      ...event,
      timestamp: ensureDate(event.timestamp)
    };
  });

  const sortedEvents = [...normalizedEvents].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

  const eventListContent = (
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

          return (
            <Card
              key={event.id}
              className={`p-4 transition-all duration-200 relative ${
                getEventColor(event.type)
              } ${
                event.type === 'agent_reasoning' ? 'border-l-4 border-l-primary' :
                event.type === 'move_analysis' ? 'border-l-4 border-l-brand-orange' : ''
              } ${
                hasExpandableContent
                  ? 'cursor-pointer hover:bg-opacity-80 hover:shadow-md border-2 border-transparent hover:border-border/60'
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
                {/* Top row with number first, then icon, badge, timestamp, and chevron */}
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex-shrink-0 w-5 h-5 bg-muted/40 border border-border/50 rounded-full flex items-center justify-center">
                    <span className="text-[10px] font-mono text-muted-foreground font-medium">
                      {sortedEvents.length - sortedEvents.indexOf(event)}
                    </span>
                  </div>
                  <div className="flex-shrink-0">
                    {getEventIcon(event.type)}
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-xs capitalize px-2.5 py-1 flex-shrink-0 ${
                      event.type === 'agent_reasoning'
                        ? 'bg-primary/15 border-primary/30 text-primary'
                        : event.type === 'move_analysis'
                        ? 'bg-brand-orange/15 border-brand-orange/30 text-brand-orange'
                        : ''
                    }`}
                  >
                    {event.type === 'agent_reasoning' ? 'Agent' :
                     event.type === 'move_analysis' ? 'Analysis' :
                     event.type === 'game_event' ? 'Game' :
                     event.type.replace('_', ' ')}
                  </Badge>
                  <div className="flex-1 min-w-0"></div>
                  <span
                    className="text-xs font-mono opacity-75 flex-shrink-0"
                    data-testid="event-timestamp"
                  >
                    {formatTimestamp(event.timestamp)}
                  </span>

                  {/* Chevron aligned with the title row */}
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

                {/* Content row - full width for reasoning text */}
                <div className="w-full">
                  <div className="text-sm font-medium leading-relaxed break-words" data-testid="event-content">
                    {formatEventMessage(event)}
                  </div>
                </div>

                {/* Expanded content */}
                {hasExpandableContent && isExpanded && (
                  <div className="w-full">
                    <div className="p-4 bg-muted/30 rounded-lg border border-border/40 animate-in slide-in-from-top-2 duration-200">
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
  );

  // If noCard is true, render without the Card wrapper
  if (noCard) {
    return (
      <div
        className={`w-full h-full ${className}`}
        style={{ maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight }}
        data-testid="event-log-sidebar"
      >
        <div className="h-full max-h-full overflow-y-auto scrollbar-visible">
          {eventListContent}
        </div>
      </div>
    );
  }

  // Default: render with Card wrapper
  return (
    <Card
      className={`w-full max-w-md h-full flex flex-col rounded-xl ${noMargin ? '' : 'mb-4'} ${className}`}
      style={{ maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight }}
      data-testid="event-log-sidebar"
    >
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Event Log
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-hidden p-0">
        <div className="h-full max-h-full pl-6 pr-4 py-2 overflow-y-auto scrollbar-visible">
          {eventListContent}
        </div>
      </CardContent>
    </Card>
  );
};
