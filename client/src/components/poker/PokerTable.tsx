import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card as UICard, CardContent } from '@/components/ui/card';
import PlayerSeat from './PlayerSeat';
import { Card, TexasHoldemEvent } from '@/services/pokerApi';
import { ChevronDown } from 'lucide-react';
import { PlayerId, AgentVersionId } from '@/types/ids';
import { EventLog, GameEvent } from './EventLog';
import { ChatWindow } from '@/components/games/ChatWindow';
import { agentsService } from '@/services/agentsService';

interface Player {
  id: PlayerId;
  name: string;
  chipCount: number;
  agentVersionId?: AgentVersionId;
  cards?: Card[];
  isActive?: boolean;
  isFolded?: boolean;
  isAllIn?: boolean;
  currentBet?: number;
  isDealer?: boolean;
  isSmallBlind?: boolean;
  isBigBlind?: boolean;
  isEmpty?: boolean;
  action?: string;
  position?: number;
}

interface PokerTableProps {
  players?: Player[];
  communityCards?: Card[];
  pot?: number;
  currentPlayerId?: string;
  isPlayerTurn?: boolean;
  processingAction?: boolean;
  className?: string;
  events?: (GameEvent | TexasHoldemEvent)[]; // Game events for the event log
  isPlayground?: boolean; // Whether this is a playground game
  showAgentPlayButton?: boolean; // TEMPORARY: Whether to show agent play button in non-playground games
  onViewEventLog?: () => void; // Callback for viewing event log
  onAction: (action: 'fold' | 'call' | 'raise') => void;
  onAgentTurn: () => void;
}

export const PokerTable: React.FC<PokerTableProps> = ({
  players = [],
  communityCards = [],
  pot = 1250,
  currentPlayerId,
  isPlayerTurn = false,
  processingAction = false,
  events = [],
  isPlayground = false,
  showAgentPlayButton = false,
  onViewEventLog,
  onAction,
  onAgentTurn
}) => {
  const [agentAvatars, setAgentAvatars] = useState<Record<string, { avatarUrl?: string | null; avatarType?: string }>>({});

  // Only use actual players, don't create empty seats
  const allSeats = players.filter(player => !player.isEmpty);

  // Fetch agent avatars when players change
  useEffect(() => {
    const loadAgentAvatars = async () => {
      if (!players || players.length === 0) return;

      try {
        const agentVersionIds = players.map(p => p.agentVersionId).filter(Boolean) as AgentVersionId[];
        if (agentVersionIds.length === 0) return;

        const avatars = await agentsService.getAgentAvatarsFromVersionIds(agentVersionIds);

        // Map avatars by player ID instead of agent version ID
        const playerAvatars: Record<string, { avatarUrl?: string | null; avatarType?: string }> = {};
        players.forEach(player => {
          if (player.agentVersionId) {
            const avatarInfo = avatars[player.agentVersionId];
            if (avatarInfo) {
              playerAvatars[player.id] = avatarInfo;
            }
          }
        });

        setAgentAvatars(playerAvatars);
      } catch (error) {
        console.error('[PokerTable] Failed to load agent avatars:', error);
      }
    };

    loadAgentAvatars();
  }, [players]);

  const currentPlayer = allSeats.find(p => p.isActive || p.id === currentPlayerId) || null;



  return (
    <div className="w-full h-full flex gap-4">
      {/* Main Game Content Area */}
      <div className="flex-1 min-w-0">
        <div className="w-full max-w-6xl mx-auto grid grid-cols-12 gap-6 items-center h-full">
          {/* Main Table Area - 9 columns */}
          <div className="col-span-9">
            <div className="relative w-full aspect-[2/1] bg-[#2a4d31] rounded-full border-8 border-[#39583f] shadow-2xl p-20">
              {/* Inner dashed border */}
              <div className="absolute inset-0 rounded-full border-8 border-dashed border-[#4d6555] m-10"></div>

              <div className="relative w-full h-full">
                {/* Community Cards in Center */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex gap-2">
                  {communityCards.map((card, index) => {
                    const getSuitSymbol = (suit: string): string => {
                      switch (suit) {
                        case 'hearts':
                          return '♥';
                        case 'diamonds':
                          return '♦';
                        case 'clubs':
                          return '♣';
                        case 'spades':
                          return '♠';
                        default:
                          return suit;
                      }
                    };

                    const suitSymbol = getSuitSymbol(card.suit);
                    const isRed = suitSymbol === '♥' || suitSymbol === '♦';

                    return (
                      <div key={index} className="w-16 h-24 bg-white rounded-xl border-2 border-gray-300 flex items-center justify-center text-black text-3xl font-bold shadow-lg">
                        <span className={isRed ? 'text-red-500' : 'text-black'}>
                          {card.rank}{suitSymbol}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Total Pot Display */}
                <div className="absolute bottom-[20%] left-1/2 -translate-x-1/2 text-center">
                  <p className="text-lg font-bold text-white">Total Pot: ${pot.toLocaleString()}</p>
                </div>

                {allSeats.map((player) => {
                  const playerPosition = player.position || 1;
                  const isPlayerActive = player.isActive;
                  const isProcessing = isPlayerActive && processingAction;

                  return (
                    <PlayerSeat
                      key={`player-${playerPosition}-${player.id}`}
                      playerId={player.id}
                      playerName={player.name}
                      chipCount={player.chipCount}
                      cards={player.cards}
                      isActive={isPlayerActive}
                      isProcessing={isProcessing}
                      isFolded={player.isFolded}
                      isAllIn={player.isAllIn}
                      currentBet={player.currentBet}
                      position={playerPosition}
                      isEmpty={false}
                      isDealer={player.isDealer}
                      isSmallBlind={player.isSmallBlind}
                      isBigBlind={player.isBigBlind}
                      action={player.action}
                    />
                  );
                })}
              </div>
            </div>
          </div>

          {/* Control Sidebar - 3 columns */}
          <div className="col-span-3 h-full">
            <UICard className="w-full h-full flex flex-col gap-4 p-6 overflow-y-auto">
              {/* Current Player Info */}
              <UICard className="bg-[#1a2d21] border-[#29382f]">
                <CardContent className="p-6">
                  <h3 className="text-lg font-bold leading-tight tracking-[-0.015em] mb-4 text-white">
                    Current Player: <span className="text-white font-bold">{currentPlayer?.name || 'Waiting...'}</span>
                  </h3>
                </CardContent>
              </UICard>


              {/* Action Buttons */}
              <div className="flex flex-col gap-4">
                {/* Show agent play button in playground mode OR in real games when flag is enabled */}
                {(isPlayground || showAgentPlayButton) && (
                  <Button
                    className={`flex w-full items-center justify-center rounded-xl h-12 px-6 text-base font-bold tracking-wide transition-colors ${
                      isPlayground
                        ? "bg-[#38e07b] text-[#111714] hover:bg-green-400"
                        : "bg-brand-orange text-white hover:bg-brand-orange/90"
                    }`}
                    onClick={() => onAgentTurn()}
                    disabled={!isPlayerTurn || processingAction}
                  >
                    Play Agent Turn
                  </Button>
                )}

                {/* View Event Log Button */}
                {onViewEventLog && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-[#3d5245] text-white hover:bg-[#4a6354] border-[#29382f] rounded-xl"
                    onClick={onViewEventLog}
                  >
                    View Event Log
                  </Button>
                )}

                {/* Manual Actions Dropdown */}
                <UICard className="bg-[#1a2d21] border-[#29382f]">
                  <details className="group">
                    <summary className="flex cursor-pointer items-center justify-between gap-4 p-4 text-sm font-medium list-none text-white">
                      Manual Actions
                      <div className="text-white group-open:rotate-180 transition-transform">
                        <ChevronDown className="w-5 h-5" />
                      </div>
                    </summary>
                    <div className="grid grid-cols-3 gap-2 p-4 border-t border-[#29382f]">
                      <Button
                        variant="outline"
                        size="sm"
                        className="bg-[#3d5245] text-white hover:bg-[#4a6354] border-[#29382f] rounded-xl"
                        onClick={() => onAction('fold')}
                        disabled={!isPlayerTurn || processingAction}
                      >
                        Fold
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="bg-[#3d5245] text-white hover:bg-[#4a6354] border-[#29382f] rounded-xl"
                        onClick={() => onAction('call')}
                        disabled={!isPlayerTurn || processingAction}
                      >
                        Call
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="bg-blue-600 text-white hover:bg-blue-500 border-blue-500 rounded-xl"
                        onClick={() => onAction('raise')}
                        disabled={!isPlayerTurn || processingAction}
                      >
                        Raise
                      </Button>
                    </div>
                  </details>
                </UICard>
              </div>
            </UICard>
          </div>
        </div>
      </div>

      {/* Event Log / Chat Window Sidebar - positioned to the right with margin */}
      <div className="w-80 flex-shrink-0">
        {isPlayground ? (
          <UICard className="h-full flex flex-col">
            <ChatWindow
              messages={events
                .filter((e: any) => e.type === 'chat_message')
                .map((e: any) => ({
                  playerId: e.player_id || e.playerId,
                  message: e.message,
                  timestamp: e.timestamp,
                }))}
              playerNames={players.reduce((acc: Record<string, string>, p) => {
                acc[p.id] = p.name;
                return acc;
              }, {})}
              playerAvatars={agentAvatars}
            />
          </UICard>
        ) : (
          <EventLog events={events} players={players} className="h-full" />
        )}
      </div>
    </div>
  );
};

export default PokerTable;
