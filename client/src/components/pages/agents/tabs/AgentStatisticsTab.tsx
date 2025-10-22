import React, { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { GameEnvironment } from "@/services/agentsService";
import { Badge } from "@/components/ui/badge";
import { agentsService, type AgentStatisticsResponse } from "@/services/agentsService";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Trophy,
  Target,
  Clock,
  Activity,
  Gamepad2
} from "lucide-react";
import { type AgentId } from "@/types/ids";

interface AgentStatisticsTabProps {
  agentId: AgentId;
  environment?: GameEnvironment;
}

export const AgentStatisticsTab: React.FC<AgentStatisticsTabProps> = ({
  agentId,
  environment,
}) => {
  const [statistics, setStatistics] = useState<AgentStatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatistics();
  }, [agentId]);

  const loadStatistics = async () => {
    try {
      setLoading(true);
      const stats = await agentsService.getStatistics(agentId);
      console.log("Loaded statistics for agent:", agentId, stats);
      setStatistics(stats);
    } catch (error) {
      console.error("Failed to load statistics for agent:", agentId, error);
    } finally {
      setLoading(false);
    }
  };

  

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-teal mx-auto mb-4"></div>
        <p className="text-muted-foreground">Loading statistics...</p>
      </div>
    );
  }

  if (!statistics) {
    return (
      <div className="text-center py-8">
        <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
        <h3 className="text-lg font-semibold text-foreground mb-2">No Statistics Available</h3>
        <p className="text-muted-foreground mb-2">
          Statistics will appear here once your agent plays competitive games.
        </p>
        <p className="text-sm text-muted-foreground">
          Note: Playground games don't count towards statistics.
        </p>
      </div>
    );
  }

  // Ensure statistics has all required fields with defaults
  const stats = {
    ...statistics.statistics,
    gamesPlayed: statistics.statistics.gamesPlayed ?? 0,
    totalWinnings: statistics.statistics.totalWinnings ?? 0,
    totalLosses: statistics.statistics.totalLosses ?? 0,
    netBalance: statistics.statistics.netBalance ?? 0,
    winRate: statistics.statistics.winRate ?? 0,
    gamesWon: statistics.statistics.gamesWon ?? 0,
    gamesLost: statistics.statistics.gamesLost ?? 0,
    gamesDrawn: statistics.statistics.gamesDrawn ?? 0,
    sessionTimeSeconds: statistics.statistics.sessionTimeSeconds ?? 0,
    longestGameSeconds: statistics.statistics.longestGameSeconds ?? 0,
    shortestGameSeconds: statistics.statistics.shortestGameSeconds ?? null,
    gameRatings: statistics.statistics.gameRatings ?? {},
    recentForm: statistics.statistics.recentForm ?? [],
    environmentSpecificData: statistics.statistics.environmentSpecificData ?? {},
    customMetrics: statistics.statistics.customMetrics ?? {},
  };
  const pokerStats = stats.environmentSpecificData?.poker;

  const formatCurrency = (amount: number | undefined | null) => {
    if (amount === undefined || amount === null || isNaN(amount)) {
      return "$0.00";
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(amount);
  };

  const formatPercentage = (value: number | undefined | null) => {
    if (value === undefined || value === null || isNaN(value)) {
      return "0.0%";
    }
    return `${value.toFixed(1)}%`;
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-2">Agent Statistics</h3>
        <p className="text-muted-foreground">
          Performance metrics and analytics for your agent's gameplay.
        </p>
        {statistics.updatedAt && (
          <p className="text-sm text-muted-foreground mt-1">
            Last updated: {new Date(statistics.updatedAt).toLocaleString()}
          </p>
        )}
      </div>

      {/* Overall Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-brand-teal" />
              Games Played
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.gamesPlayed}</div>
            <p className="text-xs text-muted-foreground">
              {stats.gamesWon} W / {stats.gamesLost} L / {stats.gamesDrawn} D
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Target className="h-4 w-4 text-brand-orange" />
              Win Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercentage(stats.winRate)}</div>
            <div className="flex items-center gap-1 text-xs">
              {stats.winRate >= 50 ? (
                <TrendingUp className="h-3 w-3 text-green-500" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-500" />
              )}
              <span className={stats.winRate >= 50 ? "text-green-600" : "text-red-600"}>
                {stats.winRate >= 50 ? "Above average" : "Below average"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-brand-mint" />
              Net Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${stats.netBalance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(stats.netBalance)}
            </div>
            <p className="text-xs text-muted-foreground">
              +{formatCurrency(stats.totalWinnings)} / -{formatCurrency(stats.totalLosses)}
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4 text-brand-teal" />
              Session Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatDuration(stats.sessionTimeSeconds)}</div>
            <p className="text-xs text-muted-foreground">
              {stats.longestGameSeconds > 0 && (
                <>Longest: {formatDuration(stats.longestGameSeconds)}</>
              )}
              {stats.shortestGameSeconds !== null && stats.shortestGameSeconds > 0 && (
                <>{stats.longestGameSeconds > 0 ? ' • ' : ''}Shortest: {formatDuration(stats.shortestGameSeconds)}</>
              )}
              {stats.longestGameSeconds === 0 && stats.shortestGameSeconds === null && (
                <>Total playing time in real games</>
              )}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Game-Specific Ratings */}
      {stats.gameRatings && Object.keys(stats.gameRatings).length > 0 && (
        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gamepad2 className="h-5 w-5 text-brand-orange" />
              Game Ratings
            </CardTitle>
            <CardDescription>
              Your agent's performance across different game types.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(stats.gameRatings).map(([gameType, rating]: [string, any]) => (
                <div key={gameType} className="p-4 bg-muted/30 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium capitalize">{gameType.replace(/_/g, ' ')}</span>
                    <Badge variant="secondary" className="bg-brand-teal text-white">
                      {Math.round(rating.rating)}
                    </Badge>
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Games:</span>
                      <span className="font-medium">{rating.gamesPlayed || 0}</span>
                    </div>
                    {rating.gamesWon !== undefined && (
                      <div className="flex justify-between">
                        <span>Record:</span>
                        <span className="font-medium">
                          {rating.gamesWon || 0}W-{rating.gamesLost || 0}L-{rating.gamesDrawn || 0}D
                        </span>
                      </div>
                    )}
                    {rating.highestRating && (
                      <div className="flex justify-between">
                        <span>Peak:</span>
                        <span className="font-medium text-green-600">{Math.round(rating.highestRating)}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Form */}
      {stats.recentForm && stats.recentForm.length > 0 && (
        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-brand-teal" />
              Recent Form
            </CardTitle>
            <CardDescription>
              Last {stats.recentForm.length} games performance trend.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {stats.recentForm.map((game: any, idx: number) => {
                const ratingChange = game.ratingChange ?? 0;
                const gameType = game.gameType ?? 'Unknown';
                const result = game.result ?? 'loss';

                return (
                  <div
                    key={idx}
                    className={`px-3 py-2 rounded-lg text-sm font-medium ${
                      result === 'win'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : result === 'draw'
                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    }`}
                    title={`${gameType}: ${result} (${ratingChange >= 0 ? '+' : ''}${ratingChange.toFixed(0)})`}
                  >
                    {result === 'win' ? 'W' : result === 'draw' ? 'D' : 'L'}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}



      {/* Poker-Specific Statistics */}
      {pokerStats && (
        <>
          <Card className="relative overflow-hidden">
            <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-brand-orange" />
                Best Hand
              </CardTitle>
              <CardDescription>
                Your agent's highest winning hand and pot size.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-semibold">{pokerStats.bestHand?.description ?? "N/A"}</div>
                  <p className="text-sm text-muted-foreground">
                    Hand value: {pokerStats.bestHand?.value ?? 0}
                  </p>
                </div>
                <Badge className="bg-brand-orange text-white">
                  {formatCurrency(pokerStats.bestHand?.potSize ?? 0)}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Average Pot Won</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{formatCurrency(pokerStats.averagePotWon)}</div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Biggest Bluff</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{formatCurrency(pokerStats.biggestBluffWon)}</div>
                <p className="text-xs text-muted-foreground">Largest pot won without best hand</p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Fold Percentage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{formatPercentage(pokerStats.foldPercentage ?? 0)}</div>
                <p className="text-xs text-muted-foreground">
                  {pokerStats.handsFolded ?? 0} of {pokerStats.totalHandsPlayed ?? 0} hands
                </p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">VPIP</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{formatPercentage(pokerStats.vpip ?? 0)}</div>
                <p className="text-xs text-muted-foreground">Voluntarily put money in pot</p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Aggression Factor</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{(pokerStats.aggressionFactor ?? 0).toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">
                  {pokerStats.totalRaises ?? 0} raises, {pokerStats.totalCalls ?? 0} calls
                </p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Hands Won</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">
                  {pokerStats.handsWon}/{pokerStats.totalHandsPlayed}
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatPercentage((pokerStats.totalHandsPlayed > 0 ? (pokerStats.handsWon / pokerStats.totalHandsPlayed) * 100 : 0))} win rate
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {/* Custom Metrics */}
      {stats.customMetrics && Object.keys(stats.customMetrics).length > 0 && (
        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Custom Metrics
            </CardTitle>
            <CardDescription>
              Additional performance metrics specific to your agent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(stats.customMetrics).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center p-3 bg-muted/30 rounded-lg">
                  <span className="font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                  <span className="text-lg font-semibold">{JSON.stringify(value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AgentStatisticsTab;
