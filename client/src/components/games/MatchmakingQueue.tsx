/**
 * Matchmaking queue component showing status and countdown.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Loader2, Users, Clock, X, Gamepad2 } from 'lucide-react';
import { toast } from 'sonner';
import { gameMatchingApi } from '@/services/gameMatchingApi';
import { useNavigate } from 'react-router-dom';

interface MatchmakingQueueProps {
  gameId: string;
  gameType: string;
  onGameStarted?: (gameId: string) => void;
  onCancelled?: () => void;
  onStatusUpdate?: (s: MatchmakingStatusResponseExtended) => void;
}

interface MatchmakingStatusResponseExtended {
  gameId: string | null;
  gameType: string | null;
  matchmakingStatus: string | null;
  currentPlayers: number;
  minPlayers: number;
  maxPlayers: number;
  waitingDeadline: string | null;
  timeRemainingSeconds: number | null;
  allowsMidgameJoining?: boolean;
}

export const MatchmakingQueue: React.FC<MatchmakingQueueProps> = ({
  gameId,
  gameType: _gameType,
  onGameStarted,
  onCancelled,
  onStatusUpdate,
}) => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<MatchmakingStatusResponseExtended | null>(null);
  const [loading, setLoading] = useState(false);
  const pollingActiveRef = useRef(false);

  // Long polling for status updates
  useEffect(() => {
    // Prevent multiple polling loops from starting
    if (pollingActiveRef.current) {
      console.warn('Polling already active, skipping duplicate effect');
      return;
    }

    pollingActiveRef.current = true;
    let isActive = true;
    console.log('[MatchmakingQueue] Starting polling loop');

    const pollStatus = async () => {
      while (isActive) {
        try {
          console.log('[MatchmakingQueue] Sending long-poll request...');
          const currentStatus = await gameMatchingApi.getMatchmakingStatus(30);
          console.log('[MatchmakingQueue] Received response:', currentStatus);

          if (!isActive) break; // Component unmounted during request

          // If no active game, user left/cancelled matchmaking
          if (!currentStatus.gameId) {
            onCancelled?.();
            break;
          }

          setStatus(currentStatus);

          // Notify parent with the latest status (for header progress)
          onStatusUpdate?.(currentStatus);

          // If game started, navigate to it
          if (currentStatus.matchmakingStatus === 'in_progress' && currentStatus.gameId) {
            onGameStarted?.(currentStatus.gameId);

            // Navigate based on game type
            if (currentStatus.gameType === 'texas_holdem') {
              navigate(`/games/texas-holdem/${currentStatus.gameId}`);
            } else if (currentStatus.gameType === 'chess') {
              navigate(`/games/chess/${currentStatus.gameId}`);
            }
            break; // Stop polling after navigation
          }
        } catch (error) {
          console.error('[MatchmakingQueue] Error polling matchmaking status:', error);
          // Wait a bit before retrying on error
          if (isActive) {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        }
      }
      console.log('[MatchmakingQueue] Polling loop ended');
    };

    pollStatus();

    // Cleanup on unmount
    return () => {
      console.log('[MatchmakingQueue] Cleaning up polling loop');
      isActive = false;
      pollingActiveRef.current = false;
    };
  }, [gameId]); // Only depend on gameId to prevent re-running

  // Handle leaving queue
  const handleLeaveQueue = async () => {
    setLoading(true);
    try {
      await gameMatchingApi.leaveMatchmaking(gameId);
      toast.success('Left matchmaking queue');
      onCancelled?.(); // This will unmount the component, triggering cleanup
    } catch (error) {
      console.error('Error leaving queue:', error);
      toast.error('Failed to leave queue');
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-brand-teal" />
      </div>
    );
  }

  const progress = status.maxPlayers > 0
    ? (status.currentPlayers / status.maxPlayers) * 100
    : 0;

  const timeRemainingMinutes = status.timeRemainingSeconds
    ? Math.floor(status.timeRemainingSeconds / 60)
    : 0;
  const timeRemainingSeconds = status.timeRemainingSeconds
    ? status.timeRemainingSeconds % 60
    : 0;

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gamepad2 className="h-5 w-5 text-brand-teal" />
          <span className="text-lg font-semibold">Finding Match</span>
        </div>
        <Badge variant="outline" className="text-brand-teal border-brand-teal">
          {status.matchmakingStatus}
        </Badge>
      </div>

      <div className="space-y-6">
        {/* Player count */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-brand-orange" />
              <span className="font-medium">Players</span>
            </div>
            <span className="text-muted-foreground">
              {status.currentPlayers} / {status.maxPlayers}
            </span>
          </div>
          <Progress value={progress} className="h-2" />
          <p className="text-xs text-muted-foreground text-center">
            {status.minPlayers - status.currentPlayers > 0
              ? `Need ${status.minPlayers - status.currentPlayers} more player(s) to start`
              : 'Ready to start!'}
          </p>
        </div>

        {/* Countdown timer */}
        {status.timeRemainingSeconds !== null && status.timeRemainingSeconds > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-brand-orange" />
                <span className="font-medium">Time Remaining</span>
              </div>
              <span className="text-muted-foreground font-mono">
                {timeRemainingMinutes}:{timeRemainingSeconds.toString().padStart(2, '0')}
              </span>
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Game will start with system agents if not enough players join
            </p>
          </div>
        )}

        {/* Mid-game joining info */}
        {status.allowsMidgameJoining && (
          <div className="text-center">
            <p className="text-xs text-muted-foreground">
              You can join this game even after it starts!
            </p>
          </div>
        )}

        {/* Loading indicator */}
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Searching for players...</span>
        </div>

        {/* Cancel button */}
        <Button
          variant="outline"
          className="w-full rounded-md"
          onClick={handleLeaveQueue}
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Leaving...
            </>
          ) : (
            <>
              <X className="mr-2 h-4 w-4" />
              Leave Queue
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

