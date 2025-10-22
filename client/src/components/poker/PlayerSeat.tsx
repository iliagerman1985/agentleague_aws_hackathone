import React from 'react';
import { cn } from '@/lib/utils';
import { Card, CardSuit } from '@/services/pokerApi';
import { Loader2 } from 'lucide-react';

// Convert CardSuit enum values to Unicode symbols
const getSuitSymbol = (suit: CardSuit | string): string => {
  switch (suit) {
    case CardSuit.HEARTS:
    case 'hearts':
      return '♥';
    case CardSuit.DIAMONDS:
    case 'diamonds':
      return '♦';
    case CardSuit.CLUBS:
    case 'clubs':
      return '♣';
    case CardSuit.SPADES:
    case 'spades':
      return '♠';
    default:
      return suit; // Return as-is if already a symbol
  }
};

interface PlayerSeatProps {
  playerId?: string;
  playerName?: string;
  chipCount?: number;
  cards?: Card[];
  isActive?: boolean;
  isProcessing?: boolean;
  isFolded?: boolean;
  isAllIn?: boolean;
  currentBet?: number;
  position: number; // 1-10 for 10 players
  isEmpty?: boolean;
  className?: string;
  isDealer?: boolean;
  isSmallBlind?: boolean;
  isBigBlind?: boolean;
  action?: string; // Current action like 'Call', 'Raise', 'Fold', etc.
}

// Get player color based on position (1-10)
const getPlayerColor = (position: number): string => {
  return `var(--player-${position}-color)`;
};

// Get action status styling
const getActionStyling = (action?: string, isFolded?: boolean) => {
  if (isFolded) return 'bg-red-900/50 backdrop-blur-sm';
  if (action === 'Raise') return 'bg-gray-900/50 backdrop-blur-sm';
  if (action === 'Call') return 'bg-gray-900/50 backdrop-blur-sm';
  if (action === 'Check') return 'bg-gray-900/50 backdrop-blur-sm';
  if (action === 'Fold') return 'bg-red-900/50 backdrop-blur-sm';
  return 'bg-gray-900/50 backdrop-blur-sm';
};

export const PlayerSeat: React.FC<PlayerSeatProps> = ({
  playerId: _playerId,
  playerName = 'Agent',
  chipCount = 0,
  cards = [],
  isActive = false,
  isProcessing = false,
  isFolded = false,
  isAllIn: _isAllIn = false,
  currentBet = 0,
  position,
  isEmpty = false,
  className,
  isDealer = false,
  isSmallBlind = false,
  isBigBlind = false,
  action
}) => {
  const playerColor = getPlayerColor(position);
  const actionStyling = getActionStyling(action, isFolded);

  // Don't render empty seats at all
  if (isEmpty) {
    return null;
  }

  return (
    <>
      {/* Bet Display - Positioned using CSS classes */}
      {currentBet > 0 && (
        <div className={cn('bet-position', `bet-${position}`, 'flex items-center gap-2')}>
          <div
            className="w-6 h-6 rounded-full border-2 border-white"
            style={{ backgroundColor: playerColor }}
          ></div>
          <span className="text-sm font-bold text-white drop-shadow-md">${currentBet.toLocaleString()}</span>
        </div>
      )}

      {/* Player Position - Using CSS classes from new design */}
      <div className={cn('player-position', `player-${position}`, 'text-center', className)}>
        {/* Cards positioned using CSS classes for all players including player 1 */}
        <div className={cn(
          'absolute flex items-center gap-1',
          `cards-player-${position}`,
          isFolded && 'opacity-50'
        )}>
          {cards && cards.length > 0 ? (
            cards.map((card, index) => {
              const suitSymbol = getSuitSymbol(card.suit);
              const isRed = suitSymbol === '♥' || suitSymbol === '♦';
              return (
                <div
                  key={index}
                  className={cn(
                    'playing-card w-16 h-24 bg-white rounded-lg border-2 border-gray-300 flex items-center justify-center text-3xl font-bold',
                    index === 0 ? '-rotate-6' : 'rotate-6'
                  )}
                >
                  <span className={isRed ? 'text-red-500' : 'text-black'}>
                    {card.rank}{suitSymbol}
                  </span>
                </div>
              );
            })
          ) : (
            <>
              <div className="w-16 h-24 bg-gray-800 rounded-lg border border-gray-500 -rotate-6 card-back"></div>
              <div className="w-16 h-24 bg-gray-800 rounded-lg border border-gray-500 rotate-6 card-back"></div>
            </>
          )}
        </div>

        {/* Player Info */}
        <div className="relative">
          <p className="text-sm font-bold" style={{ color: playerColor }}>
            {playerName}
          </p>
          <div
            className={cn(
              'relative rounded-full mx-auto mt-1 flex items-center justify-center bg-gray-800',
              isActive ? 'w-20 h-20 border-4 shadow-lg' : 'w-16 h-16 border-2'
            )}
            style={{ borderColor: isActive ? 'hsl(var(--primary))' : playerColor }}
          >
            {/* Loading spinner overlay when processing */}
            {isProcessing && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full">
                <Loader2 className="h-8 w-8 animate-spin text-white" />
              </div>
            )}

            {/* Position Indicators */}
            {isDealer && (
              <span className="absolute -top-2 -right-2 w-6 h-6 bg-[var(--dealer-chip)] text-black text-xs font-bold rounded-full flex items-center justify-center border-2 border-black">
                D
              </span>
            )}
            {isSmallBlind && (
              <span className="absolute -top-2 -right-2 w-6 h-6 bg-[var(--small-blind)] text-white text-xs font-bold rounded-full flex items-center justify-center border-2 border-black">
                SB
              </span>
            )}
            {isBigBlind && (
              <span className="absolute -top-2 -right-2 w-6 h-6 bg-[var(--big-blind)] text-white text-xs font-bold rounded-full flex items-center justify-center border-2 border-black">
                BB
              </span>
            )}
          </div>

          <p className="text-xs text-white mt-1">
            ${chipCount.toLocaleString()}
          </p>

          {/* Action Status */}
          {action && (
            <div className={cn(
              'absolute -bottom-7 left-1/2 -translate-x-1/2 rounded-md px-2 py-1 text-xs font-semibold',
              actionStyling
            )}>
              {action}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default PlayerSeat;
