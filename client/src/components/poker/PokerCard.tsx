import React from 'react';
import { cn } from '@/lib/utils';
import { CardRank, CardSuit } from '@/services/pokerApi';

interface PokerCardProps {
  suit?: CardSuit | 'hearts' | 'diamonds' | 'clubs' | 'spades';
  rank?: CardRank | string;
  isHidden?: boolean;
  className?: string;
  size?: 'small' | 'medium' | 'large';
}

const suitSymbols: Record<string, string> = {
  hearts: '♥',
  diamonds: '♦',
  clubs: '♣',
  spades: '♠'
};

const suitColors: Record<string, string> = {
  hearts: 'text-red-500',
  diamonds: 'text-red-500',
  clubs: 'text-black',
  spades: 'text-black'
};

const cardSizes = {
  small: 'w-16 h-24 text-sm',
  medium: 'w-20 h-28 text-base',
  large: 'w-24 h-36 text-lg'
};

const rankFontSizes = {
  small: 'text-lg',
  medium: 'text-2xl',
  large: 'text-3xl'
};

const suitFontSizes = {
  small: 'text-xl',
  medium: 'text-3xl',
  large: 'text-4xl'
};

export const PokerCard: React.FC<PokerCardProps> = ({
  suit,
  rank,
  isHidden = false,
  className,
  size = 'medium'
}) => {
  if (isHidden) {
    return (
      <div
        className={cn(
          'bg-gradient-to-br from-blue-800 to-blue-900 border border-blue-700 rounded-lg flex items-center justify-center shadow-lg',
          cardSizes[size],
          className
        )}
      >
        <div className="w-full h-full bg-blue-900 rounded-md flex items-center justify-center">
          <div className="text-blue-300 text-xs font-bold transform rotate-45">♠</div>
        </div>
      </div>
    );
  }

  if (!suit || !rank) {
    return (
      <div
        className={cn(
          'bg-gray-200 border border-gray-300 rounded-lg flex items-center justify-center shadow-lg',
          cardSizes[size],
          className
        )}
      >
        <div className="text-gray-400 text-xs">?</div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-white border-2 border-gray-800 rounded-lg shadow-lg relative overflow-hidden',
        cardSizes[size],
        className
      )}
    >
      {/* Top-left corner */}
      <div className={cn('absolute top-1 left-1 flex flex-col items-center leading-none', suitColors[suit])}>
        <div className={cn('font-bold', rankFontSizes[size])}>{rank}</div>
        <div className={cn('font-normal', suitFontSizes[size])}>{suitSymbols[suit]}</div>
      </div>
      
      {/* Center suit symbol */}
      <div className={cn('absolute inset-0 flex items-center justify-center', suitColors[suit])}>
        <div className={cn('font-normal', size === 'small' ? 'text-4xl' : size === 'medium' ? 'text-6xl' : 'text-7xl')}>
          {suitSymbols[suit]}
        </div>
      </div>
      
      {/* Bottom-right corner (rotated) */}
      <div className={cn('absolute bottom-1 right-1 flex flex-col items-center leading-none transform rotate-180', suitColors[suit])}>
        <div className={cn('font-bold', rankFontSizes[size])}>{rank}</div>
        <div className={cn('font-normal', suitFontSizes[size])}>{suitSymbols[suit]}</div>
      </div>
     </div>
   );
};

export default PokerCard;
