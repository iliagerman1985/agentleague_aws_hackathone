import { api } from '@/lib/api';
import { GameId, PlayerId, AgentVersionId } from '../types/ids';
import { GameType } from '../types/game';

export interface GameStateResponse {
  id: GameId;
  gameType: GameType;
  state: Record<string, any>;
  events: Array<Record<string, any>>;
  config: Record<string, any>;
  version: number;
  matchmakingStatus?: string | null;
  players: Array<{
    id: PlayerId;
    agentVersionId: AgentVersionId;
    name: string;
    rating?: number | null;
  }>;
}

export interface GameConfigOption {
  type: 'enum' | 'number' | 'boolean' | 'string';
  options?: Array<{
    value: string | number | boolean;
    label: string;
    default?: boolean;
  }>;
  min?: number;
  max?: number;
  step?: number;
  default?: any;
  label?: string;
}

export interface GameConfigOptionsResponse {
  gameType: GameType;
  defaultConfig: Record<string, any>;
  availableOptions: Record<string, GameConfigOption>;
}

export class GameApiService {
  /**
   * Get available configuration options for all game types
   */
  static async getConfigOptions(): Promise<Record<string, GameConfigOptionsResponse>> {
    const response: { config_options: Record<string, GameConfigOptionsResponse> } = await api.get('/api/v1/games/config-options');
    return response.config_options;
  }

  /**
   * Delete a game by id
   */
  static async deleteGame(gameId: GameId, opts?: { keepalive?: boolean }): Promise<void> {
    await api.delete(`/api/v1/games/${gameId}`, { keepalive: opts?.keepalive === true });
  }
  /**
   * Get unfiltered events for a game (authoritative ordering for replay)
   */
  static async getEvents(gameId: GameId): Promise<Array<Record<string, any>>> {
    return api.get(`/api/v1/games/${gameId}/events`);
  }

}
