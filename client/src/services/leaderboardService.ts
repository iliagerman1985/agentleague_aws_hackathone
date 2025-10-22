import { api } from '@/lib/api';
import { GameType } from '@/types/game';

export interface AgentGameRating {
  rating: number;
  gamesPlayed: number;
  gamesWon: number;
  gamesLost: number;
  gamesDrawn: number;
  highestRating: number;
  lowestRating: number;
}

export interface RecentGameEntry {
  gameType: string;
  result: 'win' | 'loss' | 'draw';
  ratingChange: number;
  timestamp: string;
}

export interface AgentProfileStats {
  gamesPlayed: number;
  gamesWon: number;
  gamesLost: number;
  gamesDrawn: number;
  winRate: number;
  recentForm: RecentGameEntry[];
}

export interface LeaderboardEntry {
  agentId: string;
  name: string;
  description: string;
  gameEnvironment: string;
  avatarUrl: string | null;
  avatarType: string;
  isSystem: boolean;
  createdAt: string;
  username: string | null;
  overallStats: AgentProfileStats;
  gameRatings: Record<string, AgentGameRating>;
}

class LeaderboardService {
  private static instance: LeaderboardService;

  static getInstance(): LeaderboardService {
    if (!LeaderboardService.instance) {
      LeaderboardService.instance = new LeaderboardService();
    }
    return LeaderboardService.instance;
  }

  /**
   * Get leaderboard entries sorted by rating
   * @param gameType Optional game type filter (e.g., 'texas_holdem', 'chess')
   * @param limit Maximum number of entries to return
   */
  async getLeaderboard(gameType?: GameType, limit: number = 100): Promise<LeaderboardEntry[]> {
    const params = new URLSearchParams();
    
    if (gameType) {
      params.append('game_type', gameType);
    }
    params.append('limit', limit.toString());

    const url = `/api/v1/leaderboard${params.toString() ? `?${params.toString()}` : ''}`;
    return api.get(url);
  }

  /**
   * Get display name for game environment
   */
  getGameEnvironmentDisplay(gameEnv: string): string {
    const displayNames: Record<string, string> = {
      'texas_holdem': 'Texas Hold\'em',
      'chess': 'Chess',
      'checkers': 'Checkers',
      'go': 'Go',
    };
    return displayNames[gameEnv] || gameEnv;
  }

  /**
   * Calculate winnings from overall stats (if available from game_ratings)
   */
  calculateWinnings(entry: LeaderboardEntry, gameType?: string): number {
    if (gameType && entry.gameRatings?.[gameType]) {
      const rating = entry.gameRatings[gameType];
      if (rating && typeof rating.gamesWon === 'number' && typeof rating.gamesLost === 'number') {
        // Simple calculation: wins * 100 - losses * 50
        return (rating.gamesWon * 100) - (rating.gamesLost * 50);
      }
    }
    
    // Overall calculation across all games
    if (entry.overallStats && typeof entry.overallStats.gamesWon === 'number' && typeof entry.overallStats.gamesLost === 'number') {
      return (entry.overallStats.gamesWon * 100) - (entry.overallStats.gamesLost * 50);
    }
    
    // Fallback if no valid stats found
    return 0;
  }
}

export const leaderboardService = LeaderboardService.getInstance();
