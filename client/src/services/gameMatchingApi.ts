/**
 * Game matching API service for multiplayer matchmaking.
 */

import { api } from '@/lib/api';
import { type GameType, type MatchmakingConfig } from '@/types/game';

export interface JoinMatchmakingRequest {
  gameType: GameType;
  agentVersionId: string;
  config?: MatchmakingConfig;
}

export interface JoinMatchmakingResponse {
  gameId: string;
  matchmakingStatus: string;
  currentPlayers: number;
  minPlayers: number;
  maxPlayers: number;
  waitingDeadline: string | null;
  allowsMidgameJoining: boolean;
}

export interface MatchmakingStatusResponse {
  gameId: string | null;
  gameType: GameType | null;
  matchmakingStatus: string | null;
  currentPlayers: number;
  minPlayers: number;
  maxPlayers: number;
  waitingDeadline: string | null;
  timeRemainingSeconds: number | null;
}

export interface LeaveMatchmakingRequest {
  gameId: string;
}

export class GameMatchingApiService {
  private static instance: GameMatchingApiService;

  static getInstance(): GameMatchingApiService {
    if (!GameMatchingApiService.instance) {
      GameMatchingApiService.instance = new GameMatchingApiService();
    }
    return GameMatchingApiService.instance;
  }

  async joinMatchmaking(request: JoinMatchmakingRequest): Promise<JoinMatchmakingResponse> {
    return api.post('/api/v1/matchmaking/join', request);
  }

  async getMatchmakingStatus(timeout: number = 30): Promise<MatchmakingStatusResponse> {
    const params = new URLSearchParams();
    params.append('timeout', timeout.toString());

    // Add extra 10 seconds to HTTP timeout to allow server to respond
    const httpTimeout = (timeout + 10) * 1000;

    return api.get(`/api/v1/matchmaking/status?${params.toString()}`, { timeout: httpTimeout });
  }

  async leaveMatchmaking(gameId: string): Promise<{ message: string }> {
    return api.post('/api/v1/matchmaking/leave', { gameId: gameId });
  }
}

export const gameMatchingApi = GameMatchingApiService.getInstance();

