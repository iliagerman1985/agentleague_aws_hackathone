import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ActionButtonsProps {
  canFold?: boolean;
  canCheck?: boolean;
  canCall?: boolean;
  canRaise?: boolean;
  canAllIn?: boolean;
  callAmount?: number;
  minRaise?: number;
  maxRaise?: number;
  playerChips?: number;
  onFold?: () => void;
  onCheck?: () => void;
  onCall?: () => void;
  onRaise?: (amount: number) => void;
  onAllIn?: () => void;
  disabled?: boolean;
  className?: string;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  canFold = true,
  canCheck = false,
  canCall = false,
  canRaise = false,
  canAllIn = true,
  callAmount = 0,
  minRaise = 0,
  maxRaise = 1000,
  playerChips = 1000,
  onFold,
  onCheck,
  onCall,
  onRaise,
  onAllIn,
  disabled = false,
  className
}) => {
  const [raiseAmount, setRaiseAmount] = useState(minRaise);
  const [showRaiseInput, setShowRaiseInput] = useState(false);

  const handleRaiseClick = () => {
    if (showRaiseInput) {
      onRaise?.(raiseAmount);
      setShowRaiseInput(false);
    } else {
      setShowRaiseInput(true);
    }
  };

  const handleRaiseAmountChange = (value: string) => {
    const amount = parseInt(value) || 0;
    const clampedAmount = Math.max(minRaise, Math.min(maxRaise, amount));
    setRaiseAmount(clampedAmount);
  };

  const quickRaiseAmounts = [
    { label: 'Min', value: minRaise },
    { label: '2x', value: Math.min(callAmount * 2, maxRaise) },
    { label: '3x', value: Math.min(callAmount * 3, maxRaise) },
    { label: 'Pot', value: Math.min(callAmount * 4, maxRaise) }, // Approximate pot bet
  ];

  if (disabled) {
    return (
      <div className={cn('flex flex-col items-center space-y-2 p-4 bg-muted rounded-lg border border-border', className)}>
        <div className="text-muted-foreground text-sm">Waiting for other players...</div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col space-y-4 p-4 bg-background rounded-lg border border-border shadow-lg', className)}>
      <div className="text-center text-foreground font-semibold mb-2">Your Action</div>
      
      {/* Main Action Buttons */}
      <div className="flex flex-wrap gap-2 justify-center">
        {canFold && (
          <Button
            variant="destructive"
            onClick={onFold}
            className="min-w-20 btn-glow-fold"
          >
            Fold
          </Button>
        )}
        
        {canCheck && (
          <Button
            variant="secondary"
            onClick={onCheck}
            className="min-w-20"
          >
            Check
          </Button>
        )}
        
        {canCall && (
          <Button
            variant="default"
            onClick={onCall}
            className="min-w-20 text-black bg-[hsl(var(--accent))] hover:opacity-90 btn-glow-call"
          >
            Call ${callAmount}
          </Button>
        )}
        
        {canRaise && (
          <Button
            variant="default"
            onClick={handleRaiseClick}
            className="min-w-20 text-white bg-[hsl(var(--primary))] hover:opacity-90 btn-glow-raise"
          >
            {showRaiseInput ? 'Confirm' : 'Raise'}
          </Button>
        )}
        
        {canAllIn && (
          <Button
            variant="destructive"
            onClick={onAllIn}
            className="min-w-20"
          >
            All-In ${playerChips}
          </Button>
        )}
      </div>

      {/* Raise Input Section */}
      {showRaiseInput && canRaise && (
        <div className="space-y-3 p-3 bg-muted/50 rounded border border-border">
          <Label htmlFor="raise-amount" className="text-foreground text-sm">
            Raise Amount (${minRaise} - ${maxRaise})
          </Label>
          
          <div className="flex space-x-2">
            <Input
              id="raise-amount"
              type="number"
              value={raiseAmount}
              onChange={(e) => handleRaiseAmountChange(e.target.value)}
              min={minRaise}
              max={maxRaise}
              className="flex-1"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRaiseInput(false)}
            >
              Cancel
            </Button>
          </div>

          {/* Quick Raise Buttons */}
          <div className="flex gap-1">
            {quickRaiseAmounts.map((quick) => (
              <Button
                key={quick.label}
                variant="outline"
                size="sm"
                onClick={() => setRaiseAmount(quick.value)}
                className="text-xs px-2 py-1"
              >
                {quick.label}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Player Info */}
      <div className="text-center text-sm text-muted-foreground">
        Your Chips: ${playerChips.toLocaleString()}
      </div>
    </div>
  );
};

export default ActionButtons;
