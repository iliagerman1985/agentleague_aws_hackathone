import React from 'react';
import { cn } from '@/lib/utils';

interface Pot {
  amount: number;
  eligiblePlayers?: string[];
  type: 'main' | 'side';
}

interface PotDisplayProps {
  pots?: Pot[];
  totalPot?: number;
  className?: string;
}

export const PotDisplay: React.FC<PotDisplayProps> = ({
  pots = [],
  totalPot,
  className
}) => {
  // If no pots provided, create a simple main pot
  const displayPots = pots.length > 0 ? pots : [
    { amount: totalPot || 0, type: 'main' as const }
  ];

  const mainPot = displayPots.find(pot => pot.type === 'main');
  const sidePots = displayPots.filter(pot => pot.type === 'side');
  const calculatedTotal = displayPots.reduce((sum, pot) => sum + pot.amount, 0);
  const displayTotal = totalPot || calculatedTotal;

  return (
    <div className={cn('flex flex-col items-center space-y-2', className)}>
      {/* Main Pot Display - Cleaner design */}
      <div className="flex flex-col items-center">
        <div className="bg-gradient-to-br from-amber-500 to-amber-700 text-white px-8 py-4 rounded-2xl shadow-xl border-2 border-amber-400">
          <div className="text-center">
            <div className="text-xs text-amber-100 font-medium mb-1">POT</div>
            <div className="text-3xl font-bold">
              ${displayTotal.toLocaleString()}
            </div>
            {mainPot && displayTotal !== mainPot.amount && (
              <div className="text-sm opacity-90 mt-1">
                Main: ${mainPot.amount.toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Side Pots */}
      {sidePots.length > 0 && (
        <div className="flex flex-col items-center space-y-2">
          <div className="text-yellow-300 text-sm font-semibold">Side Pots</div>
          <div className="flex flex-wrap gap-2 justify-center">
            {sidePots.map((pot, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-orange-600 to-orange-800 text-white px-3 py-2 rounded-lg shadow border border-orange-400"
              >
                <div className="text-center">
                  <div className="text-sm font-bold">
                    ${pot.amount.toLocaleString()}
                  </div>
                  {pot.eligiblePlayers && (
                    <div className="text-xs opacity-90">
                      {pot.eligiblePlayers.length} players
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pot Breakdown */}
      {displayPots.length > 1 && (
        <div className="text-xs text-gray-300 text-center space-y-1">
          <div>Pot Breakdown:</div>
          {displayPots.map((pot, index) => (
            <div key={index} className="flex justify-between space-x-4">
              <span className="capitalize">{pot.type} Pot:</span>
              <span>${pot.amount.toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {/* Pot Odds Info (if applicable) */}
      {mainPot && mainPot.amount > 0 && (
        <div className="text-xs text-gray-400 text-center">
          <div>Pot Odds & Info</div>
        </div>
      )}
    </div>
  );
};

export default PotDisplay;
