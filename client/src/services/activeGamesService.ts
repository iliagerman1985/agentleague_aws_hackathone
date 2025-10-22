/**
 * Service for managing active games and game status.
 */

import { api } from '@/lib/api';

// Base interfaces based on Pydantic models
export interface BaseGameState {
  gameId: string;
  gameType: string;
  isFinished: boolean;
  currentPlayerId: string;
  roundNumber: number;
}

export interface PlayerInfo {
  id: string;
  agentVersionId: string;
  name: string;
  rating?: number | null;
  color?: 'white' | 'black' | null;
}

export interface ActiveGame {
  id: string;
  gameType: string;
  matchmakingStatus: string;
  currentPlayers: number;
  maxPlayers: number;
  minPlayers: number;
  createdAt: string | null;
  startedAt: string | null;
  waitingDeadline: string | null;
  allowsMidgameJoining: boolean;
  isPlayground: boolean;
  userColor?: 'white' | 'black' | null;
  userAgentName?: string | null;
}

export interface GameHistory {
  id: string;
  gameType: string;
  matchmakingStatus: string;
  currentPlayers: number;
  maxPlayers: number;
  createdAt: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  isPlayground: boolean;
  hasEvents: boolean;
  finalState: BaseGameState;
  // Game result fields
  winnerId: string | null;
  winnersIds: string[];
  drawReason: string | null;
  finalChipCounts: Record<string, number> | null;
  userResult: 'won' | 'lost' | 'draw' | 'placed' | null;
  userColor?: 'white' | 'black' | null;
  userAgentName?: string | null;
}

export interface GameHistoryResponse {
  games: GameHistory[];
  total: number;
  limit: number;
  offset: number;
}

export interface UnifiedGame {
  id: string;
  gameType: string;
  matchmakingStatus: string;
  currentPlayers: number;
  maxPlayers: number;
  minPlayers: number;
  createdAt: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  isPlayground: boolean;
  isActive: boolean;
  // History-specific fields (optional)
  hasEvents?: boolean;
  userResult?: 'won' | 'lost' | 'draw' | 'placed' | null;
  winnerId?: string | null;
  winnersIds?: string[];
  drawReason?: string | null;
  finalChipCounts?: Record<string, number> | null;
  finalState?: BaseGameState;
  // Active-specific fields (optional)
  waitingDeadline?: string | null;
  allowsMidgameJoining?: boolean;
  // Chess-specific convenience
  userColor?: 'white' | 'black' | null;
  // Agent name
  userAgentName?: string | null;
}

export interface GameEvent {
  id: string;
  type: string;
  data: unknown; // Game-specific event data
  createdAt: string | null;
}

export interface GameStats {
  totalActive: number;
  waitingForPlayers: number;
  inProgress: number;
  playgrounds: number;
  totalHistory: number;
  finishedGames: number;
  cancelledGames: number;
}

class ActiveGamesService {
  private static instance: ActiveGamesService;

  static getInstance(): ActiveGamesService {
    if (!ActiveGamesService.instance) {
      ActiveGamesService.instance = new ActiveGamesService();
    }
    return ActiveGamesService.instance;
  }

  async getActiveGames(limit: number = 50): Promise<ActiveGame[]> {
    return api.get(`/api/v1/games/active?limit=${limit}`);
  }

  async getGameHistory(limit: number = 50, offset: number = 0, gameType?: string): Promise<GameHistoryResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (gameType) {
      params.append('gameType', gameType);
    }

    return api.get(`/api/v1/games/history?${params.toString()}`);
  }

  async getGameEvents(gameId: string): Promise<GameEvent[]> {
    return api.get(`/api/v1/games/${gameId}/events`);
  }
  async getDiscoverGames(limit: number = 50, includeActive: boolean = true, includeEnded: boolean = true): Promise<ActiveGame[]> {
    const params = new URLSearchParams({
      limit: String(limit),
      include_active: String(includeActive),
      include_ended: String(includeEnded),
    });
    return api.get(`/api/v1/games/discover?${params.toString()}`);
  }


  getGameTypeDisplay(gameType: string): string {
    if (!gameType) return 'Unknown Game';

    switch (gameType) {
      case 'texas_holdem':
        return 'Texas Hold\'em Poker';
      case 'chess':
        return 'Chess';
      default:
        return gameType.charAt(0).toUpperCase() + gameType.slice(1);
    }
  }

  getStatusDisplay(status: string): string {
    if (!status) return 'Unknown Status';

    // Normalize to lowercase for comparison
    const normalizedStatus = status.toLowerCase();

    switch (normalizedStatus) {
      case 'waiting':
        return 'Waiting for Players';
      case 'in_progress':
        return 'In Progress';
      case 'finished':
        return 'Finished';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ');
    }
  }

  getStatusColor(status: string): string {
    if (!status) return 'text-gray-600 bg-gray-50 border-gray-200';

    // Normalize to lowercase for comparison
    const normalizedStatus = status.toLowerCase();

    switch (normalizedStatus) {
      case 'waiting':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'in_progress':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'finished':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'cancelled':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  getGameStats(activeGames: ActiveGame[], historyGames: GameHistory[] = []): GameStats {
    const stats: GameStats = {
      totalActive: 0,
      waitingForPlayers: 0,
      inProgress: 0,
      playgrounds: 0,
      totalHistory: historyGames.length,
      finishedGames: 0,
      cancelledGames: 0,
    };

    activeGames.forEach(game => {
      if (game.isPlayground) {
        stats.playgrounds++;
      } else {
        // Only count non-playground games in active stats
        if (game.matchmakingStatus === 'waiting') {
          stats.waitingForPlayers++;
        } else if (game.matchmakingStatus === 'in_progress') {
          stats.inProgress++;
        }
      }
    });

    // totalActive = waiting + in_progress (excluding playgrounds)
    stats.totalActive = stats.waitingForPlayers + stats.inProgress;

    historyGames.forEach(game => {
      if (game.matchmakingStatus === 'finished') {
        stats.finishedGames++;
      } else if (game.matchmakingStatus === 'cancelled') {
        stats.cancelledGames++;
      }
    });

    return stats;
  }

  getTimeRemaining(deadline: string | null): string {
    if (!deadline) return 'Unknown';

    const now = new Date();
    const deadlineDate = new Date(deadline);
    const timeRemaining = deadlineDate.getTime() - now.getTime();

    if (timeRemaining <= 0) return 'Expired';

    const minutes = Math.floor(timeRemaining / (1000 * 60));
    const seconds = Math.floor((timeRemaining % (1000 * 60)) / 1000);

    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  }

  getGameUrl(game: ActiveGame | UnifiedGame): string {
    if (game.gameType === 'chess') {
      return `/games/chess/${game.id}`;
    } else if (game.gameType === 'texas_holdem') {
      return `/games/texas-holdem/${game.id}`;
    }
    return `/games/${game.gameType}/${game.id}`;
  }

  canJoinGame(game: ActiveGame | UnifiedGame): boolean {
    return (
      !game.isPlayground &&
      (game.allowsMidgameJoining ?? false) &&
      game.matchmakingStatus === 'in_progress' &&
      game.currentPlayers < game.maxPlayers
    );
  }

  canWatchGame(game: ActiveGame | UnifiedGame): boolean {
    return game.matchmakingStatus === 'in_progress' && !game.isPlayground;
  }

  // Convert ActiveGame to UnifiedGame
  activeToUnified(game: ActiveGame): UnifiedGame {
    return {
      id: game.id,
      gameType: game.gameType,
      matchmakingStatus: game.matchmakingStatus,
      currentPlayers: game.currentPlayers,
      maxPlayers: game.maxPlayers,
      minPlayers: game.minPlayers,
      createdAt: game.createdAt,
      startedAt: game.startedAt,
      finishedAt: null,
      isPlayground: game.isPlayground,
      isActive: true,
      waitingDeadline: game.waitingDeadline,
      allowsMidgameJoining: game.allowsMidgameJoining,
      userColor: game.userColor,
      userAgentName: game.userAgentName,
    };
  }

  // Convert GameHistory to UnifiedGame
  historyToUnified(game: GameHistory): UnifiedGame {
    return {
      id: game.id,
      gameType: game.gameType,
      matchmakingStatus: game.matchmakingStatus,
      currentPlayers: game.currentPlayers,
      maxPlayers: game.maxPlayers,
      minPlayers: game.maxPlayers, // History doesn't have minPlayers, use maxPlayers
      createdAt: game.createdAt,
      startedAt: game.startedAt,
      finishedAt: game.finishedAt,
      isPlayground: game.isPlayground,
      isActive: false,
      hasEvents: game.hasEvents,
      userResult: game.userResult,
      winnerId: game.winnerId,
      winnersIds: game.winnersIds,
      drawReason: game.drawReason,
      finalChipCounts: game.finalChipCounts,
      finalState: game.finalState,
      userColor: game.userColor,
      userAgentName: game.userAgentName,
    };
  }

  // Merge and sort active games and history
  mergeAndSortGames(activeGames: ActiveGame[], historyGames: GameHistory[]): UnifiedGame[] {
    const unified: UnifiedGame[] = [
      ...activeGames.map(g => this.activeToUnified(g)),
      ...historyGames.map(g => this.historyToUnified(g))
    ];

    // Sort: active games first, then by date (newest first)
    return unified.sort((a, b) => {
      // Active games always come first
      if (a.isActive && !b.isActive) return -1;
      if (!a.isActive && b.isActive) return 1;

      // Within active games, sort by startedAt or createdAt (newest first)
      if (a.isActive && b.isActive) {
        const aDate = new Date(a.startedAt || a.createdAt || 0).getTime();
        const bDate = new Date(b.startedAt || b.createdAt || 0).getTime();
        return bDate - aDate;
      }

      // Within history games, sort by finishedAt (newest first)
      const aDate = new Date(a.finishedAt || 0).getTime();
      const bDate = new Date(b.finishedAt || 0).getTime();
      return bDate - aDate;
    });
  }
}

export const activeGamesService = ActiveGamesService.getInstance();