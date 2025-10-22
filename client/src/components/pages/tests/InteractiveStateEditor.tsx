import React, { useEffect, useState, useCallback } from 'react';
import { GameEnvironment } from '@/services/agentsService';
import { ChessApiService } from '@/services/chessApi';
import { PokerApiService } from '@/services/pokerApi';
import { GameApiService } from '@/services/gameApi';
import { type AgentVersionId, type GameId } from '@/types/ids';
import { ChessGame } from '@/pages/ChessGame';
import PokerGame from '@/pages/PokerGame';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface InteractiveStateEditorProps {
  environment: GameEnvironment;
  agentVersionId: AgentVersionId;
  initialState: Record<string, any>;
  onStateChange: (newState: Record<string, any>) => void;
  onHasUnsavedChanges: (hasChanges: boolean) => void;
}

export const InteractiveStateEditor: React.FC<InteractiveStateEditorProps> = ({
  environment,
  agentVersionId,
  initialState,
  onStateChange: _onStateChange, // Not used - ChessGame/PokerGame handle their own state
  onHasUnsavedChanges,
}) => {
  const [playgroundGameId, setPlaygroundGameId] = useState<GameId | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create playground game from the initial state
  const createPlayground = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Cleanup any existing playground
      if (playgroundGameId) {
        await GameApiService.deleteGame(playgroundGameId);
      }

      let response;
      if (environment === GameEnvironment.CHESS) {
        const config = { playgroundOpponent: 'brain' };
        if (Object.keys(initialState).length === 0) {
          // Create default chess game
          response = await ChessApiService.createPlayground({
            agentId: agentVersionId,
            config,
            opponent: 'brain',
          });
        } else {
          // Create from state
          response = await ChessApiService.createPlaygroundFromState({
            agentId: agentVersionId,
            stateView: initialState,
            config,
            opponent: 'brain',
          });
        }
      } else if (environment === GameEnvironment.TEXAS_HOLDEM) {
        const config = {
          smallBlind: 10,
          bigBlind: 20,
          startingChips: 1000,
        };
        if (Object.keys(initialState).length === 0) {
          // Create default poker game
          response = await PokerApiService.createPlayground({
            agentId: agentVersionId,
            config,
          });
        } else {
          // Create from state
          response = await PokerApiService.createPlaygroundFromState({
            agentId: agentVersionId,
            stateView: initialState,
            numPlayers: 5,
            config,
          });
        }
      }

      if (response?.id) {
        setPlaygroundGameId(response.id as GameId);
        onHasUnsavedChanges(false);
      }
    } catch (err: any) {
      console.error('Failed to create playground:', err);
      setError(err.message || 'Failed to create playground');
    } finally {
      setLoading(false);
    }
  }, [environment, agentVersionId, initialState, onHasUnsavedChanges]);

  // Create playground when component mounts or state changes
  useEffect(() => {
    void createPlayground();
    // Cleanup on unmount
    return () => {
      if (playgroundGameId) {
        void GameApiService.deleteGame(playgroundGameId, { keepalive: true });
      }
    };
  }, [environment, agentVersionId]);

  // Note: We don't need to poll here because ChessGame and PokerGame components
  // already have their own long-polling logic built in. They will handle state updates.

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading interactive editor...</span>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-8">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={createPlayground} variant="outline">
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  if (!playgroundGameId) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <span className="text-muted-foreground">No playground game loaded</span>
      </Card>
    );
  }

  return (
    <div className="w-full">
      {environment === GameEnvironment.CHESS ? (
        <ChessGame initialGameId={playgroundGameId} />
      ) : (
        <PokerGame initialGameId={playgroundGameId} />
      )}
    </div>
  );
};

