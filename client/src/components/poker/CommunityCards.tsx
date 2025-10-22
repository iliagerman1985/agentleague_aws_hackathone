import React from 'react';
import { cn } from '@/lib/utils';
import { Card, CardSuit } from '@/services/pokerApi';

interface CommunityCardsProps {
  cards?: Card[];
  className?: string;
}

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

export const CommunityCards: React.FC<CommunityCardsProps> = ({
  cards = [],
  className
}) => {
  // Always render the community cards area, showing placeholders if no cards
  const displayCards = cards.length > 0 ? cards : [];
  const totalSlots = 5; // Always show 5 card slots

  return (
    <div className={cn('flex gap-2', className)}>
      {/* Render actual cards */}
      {displayCards.map((card, index) => {
        const suitSymbol = getSuitSymbol(card.suit);
        const isRed = suitSymbol === '♥' || suitSymbol === '♦';
        return (
          <div 
            key={index} 
            className="w-16 h-24 bg-white rounded-lg border-2 border-gray-300 flex flex-col items-center justify-center text-black font-bold"
          >
            <div className="text-lg">{card.rank}</div>
            <div className={cn('text-2xl', isRed ? 'text-red-500' : 'text-black')}>
              {suitSymbol}
            </div>
          </div>
        );
      })}
      
      {/* Render placeholder cards for remaining slots */}
      {Array.from({ length: totalSlots - displayCards.length }, (_, index) => (
        <div 
          key={`placeholder-${index}`}
          className="w-16 h-24 bg-[var(--poker-table-border)] rounded-lg border-2 border-[var(--poker-table-dashed-border)] flex items-center justify-center"
        >
          <span className="text-3xl font-bold text-gray-500">?</span>
        </div>
      ))}
    </div>
  );
};

export default CommunityCards;
