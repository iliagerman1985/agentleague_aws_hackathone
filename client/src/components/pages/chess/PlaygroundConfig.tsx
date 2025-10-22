import React, { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, RotateCcw, Save, FolderOpen } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { ChessPlaygroundOpponent, ChessSide } from '@/services/chessApi';
import type { ChessStateView, ChessPiece, Color, PieceType } from '@/types/chess';
import type { AgentId } from '@/types/ids';
import { EditableChessBoard } from '@/components/chess/EditableChessBoard';
import { SaveGameStateDialog } from '@/components/pages/agents/dialogs/SaveGameStateDialog';
import { SavedStatesDialog } from '@/components/pages/agents/dialogs/SavedStatesDialog';
import { GameEnvironment } from '@/services/agentsService';

export interface ChessPlaygroundConfigData {
  opponent: ChessPlaygroundOpponent;
  userSide?: ChessSide;
  initialState?: ChessStateView;
}

interface ChessPlaygroundConfigProps {
  onCreatePlayground: (config: ChessPlaygroundConfigData) => void;
  isCreating?: boolean;
  agentId?: AgentId;
}

const OPPONENT_OPTIONS: Array<{
  value: ChessPlaygroundOpponent;
  title: string;
  description: string;
  icon: string;
  accentClass: string;
}> = [
  {
    value: 'brain',
    title: 'Play Brain',
    description: 'Face the adaptive Stockfish-powered Brain for guided practice.',
    icon: '🧠',
    accentClass: 'text-brand-mint bg-brand-mint/15',
  },
  {
    value: 'self',
    title: 'Play Yourself',
    description: 'Control both sides to explore positions, variations, and lines.',
    icon: '♟️',
    accentClass: 'text-brand-orange bg-brand-orange/15',
  },
];

const SIDE_OPTIONS: Array<{
  value: ChessSide;
  title: string;
  icon: string;
}> = [
  {
    value: 'white',
    title: 'Play as White',
    icon: '♔',
  },
  {
    value: 'black',
    title: 'Play as Black',
    icon: '♚',
  },
];

// Helper to create starting board position
const createStartingBoard = (): (ChessPiece | null)[][] => {
  const board: (ChessPiece | null)[][] = Array(8).fill(null).map(() => Array(8).fill(null));

  // Rank 8 (black back rank)
  const backRank: PieceType[] = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'];
  backRank.forEach((type, i) => {
    board[0][i] = { type, color: 'black' };
  });

  // Rank 7 (black pawns)
  for (let i = 0; i < 8; i++) {
    board[1][i] = { type: 'pawn', color: 'black' };
  }

  // Rank 2 (white pawns)
  for (let i = 0; i < 8; i++) {
    board[6][i] = { type: 'pawn', color: 'white' };
  }

  // Rank 1 (white back rank)
  backRank.forEach((type, i) => {
    board[7][i] = { type, color: 'white' };
  });

  return board;
};

// Helper to create empty state
const createEmptyState = (): ChessStateView => ({
  board: createStartingBoard(),
  sideToMove: 'white' as Color,
  castlingRights: {
    whiteKingside: true,
    whiteQueenside: true,
    blackKingside: true,
    blackQueenside: true,
  },
  enPassantSquare: null,
  halfmoveClock: 0,
  fullmoveNumber: 1,
  remainingTimeMs: {},
  lastTimestampMs: null,
  capturedPieces: { white: [], black: [] },
  materialAdvantage: 0,
  isFinished: false,
  winner: null,
  drawReason: null,
});

export const ChessPlaygroundConfig: React.FC<ChessPlaygroundConfigProps> = ({ onCreatePlayground, isCreating = false, agentId }) => {
  const [opponent, setOpponent] = useState<ChessPlaygroundOpponent>('brain');
  const [userSide, setUserSide] = useState<ChessSide>('white');
  const [useCustomPosition, setUseCustomPosition] = useState(false);
  const [customState, setCustomState] = useState<ChessStateView>(createEmptyState());
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);

  const handleCreate = () => {
    onCreatePlayground({
      opponent,
      userSide: opponent === 'brain' ? userSide : undefined,
      initialState: useCustomPosition ? customState : undefined,
    });
  };

  const handleResetPosition = () => {
    setCustomState(createEmptyState());
  };

  const handleLoadState = (state: any) => {
    setCustomState(state as ChessStateView);
    setUseCustomPosition(true);
  };

  const selectedOption = useMemo(() => OPPONENT_OPTIONS.find(option => option.value === opponent) ?? OPPONENT_OPTIONS[0], [opponent]);

  const primaryLabel = opponent === 'brain' ? 'Start Practice Session' : 'Start Self-Play Session';
  const primaryDescription = opponent === 'brain'
    ? 'Brain adjusts its skill level based on your performance for optimal training.'
    : 'Use a single agent for both colors to analyze ideas without Stockfish moves.';

  return (
    <>
      <Card className="w-full max-w-4xl mx-auto rounded-xl">
        <CardHeader className="flex items-center justify-center text-center gap-3">
          <div className={cn('grid place-items-center w-10 h-10 rounded-full text-xl font-bold', selectedOption.accentClass)}>
            <span aria-hidden>{selectedOption.icon}</span>
          </div>
          <CardTitle>Chess Playground</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Select playground opponent">
            {OPPONENT_OPTIONS.map(option => {
              const isSelected = option.value === opponent;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => setOpponent(option.value)}
                  className={cn(
                    'w-full text-left rounded-lg border transition-colors px-4 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal',
                    isSelected ? 'border-brand-teal bg-white shadow-sm' : 'border-transparent bg-white/70 hover:bg-white',
                  )}
                  data-testid={`chess-opponent-${option.value}`}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn('flex h-9 w-9 items-center justify-center rounded-full text-lg font-semibold', option.accentClass)}>
                      <span aria-hidden>{option.icon}</span>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-semibold text-gray-900">{option.title}</p>
                        {isSelected && <span className="text-xs font-medium text-brand-teal">Selected</span>}
                      </div>
                      <p className="mt-1 text-sm leading-relaxed text-gray-600">{option.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Side selection - only show when playing against Brain bot */}
          {opponent === 'brain' && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Choose Your Side</label>
              <div className="grid grid-cols-2 gap-3">
                {SIDE_OPTIONS.map(option => {
                  const isSelected = option.value === userSide;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setUserSide(option.value)}
                      className={cn(
                        'flex items-center justify-center gap-2 rounded-lg border px-4 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal',
                        isSelected ? 'border-brand-teal bg-white shadow-sm' : 'border-transparent bg-white/70 hover:bg-white',
                      )}
                      data-testid={`chess-side-${option.value}`}
                    >
                      <span className="text-2xl" aria-hidden>{option.icon}</span>
                      <span className="font-medium text-gray-900">{option.title}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Custom Position Toggle */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Starting Position</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setUseCustomPosition(false)}
                className={cn(
                  'flex items-center justify-center gap-2 rounded-lg border px-4 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal',
                  !useCustomPosition ? 'border-brand-teal bg-white shadow-sm' : 'border-transparent bg-white/70 hover:bg-white',
                )}
              >
                <span className="font-medium text-gray-900">Standard Start</span>
              </button>
              <button
                type="button"
                onClick={() => setUseCustomPosition(true)}
                className={cn(
                  'flex items-center justify-center gap-2 rounded-lg border px-4 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal',
                  useCustomPosition ? 'border-brand-teal bg-white shadow-sm' : 'border-transparent bg-white/70 hover:bg-white',
                )}
              >
                <span className="font-medium text-gray-900">Custom Position</span>
              </button>
            </div>
          </div>

          {/* Editable Board - only show when custom position is selected */}
          {useCustomPosition && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">Set Up Position</label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setLoadDialogOpen(true)}
                    className="flex items-center gap-1"
                  >
                    <FolderOpen className="h-4 w-4" />
                    Load
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setSaveDialogOpen(true)}
                    className="flex items-center gap-1"
                  >
                    <Save className="h-4 w-4" />
                    Save
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleResetPosition}
                    className="flex items-center gap-1"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Reset
                  </Button>
                </div>
              </div>
              <div className="rounded-lg bg-white/60 p-4">
                <EditableChessBoard
                  state={customState}
                  onStateChange={setCustomState}
                />
              </div>
              <p className="text-xs text-gray-600 text-center">
                Drag and drop pieces to set up your desired position
              </p>
            </div>
          )}

          <div className="rounded-lg bg-white/60 p-4 text-center">
            <p className="text-sm font-medium text-gray-700">{primaryDescription}</p>
          </div>

          <Button
            onClick={handleCreate}
            disabled={isCreating}
            className="w-full rounded-lg bg-brand-teal hover:bg-brand-teal/90"
            data-testid="chess-start-playground"
          >
            {isCreating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Starting...
              </>
            ) : (
              primaryLabel
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Save/Load Dialogs */}
      <SaveGameStateDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        environment={GameEnvironment.CHESS}
        gameState={customState}
        agentId={agentId}
        onSaved={() => {
          setSaveDialogOpen(false);
        }}
      />
      <SavedStatesDialog
        open={loadDialogOpen}
        onOpenChange={setLoadDialogOpen}
        environment={GameEnvironment.CHESS}
        onLoadState={handleLoadState}
      />
    </>
  );
};

export default ChessPlaygroundConfig;

