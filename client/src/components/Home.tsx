import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Bot, Trophy, TrendingUp, Star, Flame, Users, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';

import { StatsCarousel } from "@/components/common/utility/StatsCarousel";
import type { StatItem } from "@/components/common/utility/StatsCarousel";

import { PageBackground } from "@/components/common/layout/PageBackground";

import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";

import { activeGamesService } from '@/services/activeGamesService';
import { agentsService, getAvailableGameEnvironments } from '@/services/agentsService';
import { leaderboardService } from '@/services/leaderboardService';
import { ItemCard } from '@/components/common/cards/ItemCard';
import { Badge } from '@/components/ui/badge';
import { Eye, History as HistoryIcon, Gamepad2 } from 'lucide-react';
import type { ActiveGame, GameHistory } from '@/services/activeGamesService';
import { MatchmakingModal } from '@/components/games/MatchmakingModal';
import { getAvailableGames } from '@/config/gameConfig';

interface UserStats {
  totalAgents: number;
  totalWins: number;
  totalGames: number;
  winRate: number;
  highestRating: number;
  topRank: string;
}

export const Home: React.FC = () => {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  const [activeGames, setActiveGames] = useState<ActiveGame[]>([]);
  const [historyGames, setHistoryGames] = useState<GameHistory[]>([]);
  const [loadingGames, setLoadingGames] = useState<boolean>(true);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [loadingStats, setLoadingStats] = useState<boolean>(true);
  const [matchmakingOpen, setMatchmakingOpen] = useState(false);
  const [selectedGameType, setSelectedGameType] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [active, historyResp] = await Promise.all([
          activeGamesService.getActiveGames(),
          activeGamesService.getGameHistory()
        ]);

        // Filter games by available environments
        const availableEnvs = getAvailableGameEnvironments();
        const filteredActive = active.filter(game =>
          availableEnvs.includes(game.gameType as any)
        );
        const filteredHistory = historyResp.games.filter(game =>
          availableEnvs.includes(game.gameType as any)
        );

        setActiveGames(filteredActive);
        setHistoryGames(filteredHistory.slice(0, 5));
      } catch (err) {
        console.error('Failed to load home games:', err);
      } finally {
        setLoadingGames(false);
      }
    })();
  }, []);

  // Fetch user stats
  useEffect(() => {
    (async () => {
      try {
        // Get user's agents
        const allAgents = await agentsService.list();

        // Filter agents to only include those for available environments
        const availableEnvs = getAvailableGameEnvironments();
        const agents = allAgents.filter(agent => availableEnvs.includes(agent.gameEnvironment));

        // Get leaderboard to find user's agents
        const leaderboard = await leaderboardService.getLeaderboard(undefined, 1000);

        // Filter to only user's agents
        const userAgents = leaderboard.filter(entry =>
          agents.some(agent => agent.id === entry.agentId)
        );

        // Calculate aggregated stats
        let totalWins = 0;
        let totalGames = 0;
        let highestRating = 0;
        let bestRank = userAgents.length > 0 ? leaderboard.findIndex(e => e.agentId === userAgents[0].agentId) + 1 : 0;

        userAgents.forEach(agent => {
          totalWins += agent.overallStats.gamesWon;
          totalGames += agent.overallStats.gamesPlayed;

          // Get highest rating across all game types
          Object.values(agent.gameRatings).forEach(rating => {
            if (rating.rating > highestRating) {
              highestRating = rating.rating;
            }
          });

          // Find best rank
          const rank = leaderboard.findIndex(e => e.agentId === agent.agentId) + 1;
          if (rank > 0 && (bestRank === 0 || rank < bestRank)) {
            bestRank = rank;
          }
        });

        const winRate = totalGames > 0 ? (totalWins / totalGames) * 100 : 0;

        // Determine rank title based on position
        let topRank = 'Unranked';
        if (bestRank > 0) {
          if (bestRank === 1) topRank = 'Champion';
          else if (bestRank <= 3) topRank = 'Elite';
          else if (bestRank <= 10) topRank = 'Diamond';
          else if (bestRank <= 25) topRank = 'Platinum';
          else if (bestRank <= 50) topRank = 'Gold';
          else if (bestRank <= 100) topRank = 'Silver';
          else topRank = 'Bronze';
        }

        setUserStats({
          totalAgents: agents.length,
          totalWins,
          totalGames,
          winRate,
          highestRating: Math.round(highestRating),
          topRank,
        });
      } catch (err) {
        console.error('Failed to load user stats:', err);
      } finally {
        setLoadingStats(false);
      }
    })();
  }, []);

  const handleGameSelect = (gameId: string, gameName: string) => {
    setSelectedGameType({ id: gameId, name: gameName });
    setMatchmakingOpen(true);
  };

  // Stats data for the carousel
  const statsData: StatItem[] = [
    {
      icon: <Bot className="h-5 w-5 sm:h-6 sm:w-6 text-cyan-500" />,
      label: "Total Agents",
      value: loadingStats ? "..." : userStats?.totalAgents.toString() || "0",
      description: "Active AI agents",
      variant: "cyan",
    },
    {
      icon: <Trophy className="h-5 w-5 sm:h-6 sm:w-6 text-green-500" />,
      label: "Total Wins",
      value: loadingStats ? "..." : userStats?.totalWins.toLocaleString() || "0",
      description: "Games won",
      variant: "green",
    },
    {
      icon: <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 text-blue-500" />,
      label: "Win Rate",
      value: loadingStats ? "..." : `${userStats?.winRate.toFixed(1) || "0"}%`,
      description: "Success rate",
      variant: "blue",
    },
    {
      icon: <Star className="h-5 w-5 sm:h-6 sm:w-6 text-yellow-500" />,
      label: "Best Rank",
      value: loadingStats ? "..." : userStats?.topRank || "Unranked",
      description: "Your highest ranking",
      variant: "yellow",
    }
  ];



  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-brand-orange mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <PageBackground variant="geometric">
      <div className="w-full space-y-8 p-6 lg:p-8">
        <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header - match Agents/Games/Tools */}
        <div className="relative flex items-center justify-between mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="home" opacity={0.20} variant="geometric" />
          </div>
          <div className="relative z-10 flex items-center justify-between w-full">
            <div>
              <h1 className="text-4xl font-bold text-foreground mb-0 sm:mb-2">Home</h1>
              <p className="hidden sm:block text-muted-foreground text-lg">Welcome back, {user?.fullName || user?.email}!</p>
            </div>
          </div>
        </div>

        {/* Stats Carousel */}
        <StatsCarousel stats={statsData} />

        {/* Top Trending Games */}
        <div className="w-full">
          <div className="flex items-center gap-2 mb-4">
            <Flame className="h-5 w-5 text-orange-500" />
            <h3 className="text-foreground text-lg sm:text-xl font-semibold">Top Trending Games</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {/* Dynamically render only available games */}
            {getAvailableGames().map((game) => (
              <ItemCard
                key={game.id}
                size="lg"
                environment={game.id}
                showEnvironmentArt={false}
                backgroundImage={game.image}
                title={game.title}
                description={game.description}
                headerBadge={
                  <Badge variant="default" className="mt-1">
                    Available
                  </Badge>
                }
                meta={
                  <>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Users className="h-4 w-4" />
                      <span>Up to {game.maxPlayers} players</span>
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground whitespace-nowrap">
                      <Clock className="h-4 w-4" />
                      <span>{game.estimatedTime}</span>
                    </div>
                  </>
                }
                features={
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-foreground">Features:</h4>
                    <div className="flex flex-wrap gap-1">
                      {game.features.map((feature, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </div>
                }
                actions={
                  <Button
                    size="lg"
                    className="w-full rounded-md bg-brand-teal hover:bg-brand-teal/90 text-base font-semibold"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleGameSelect(game.id, game.title);
                    }}
                  >
                    Play
                  </Button>
                }
                clickable
                onClick={() => handleGameSelect(game.id, game.title)}
              />
            ))}
          </div>
        </div>

        {/* Main Content Area - mobile responsive */}
        <div className="flex flex-col xl:flex-row gap-6">
          {/* Active Games */}
          <div className="w-full xl:min-w-[800px] xl:flex-1">
            <div className="bg-card border rounded-xl overflow-hidden">
              <div className="p-4 sm:p-6 pb-0">
                <h3 className="text-foreground text-lg sm:text-xl font-semibold mb-4 sm:mb-6">Active Games</h3>
              </div>
              <div className="p-4 sm:p-6 pt-0">
                {loadingGames ? (
                  <div className="flex items-center justify-center h-40"><div className="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-brand-orange" /></div>
                ) : activeGames.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No active games. <button className="underline" onClick={() => navigate('/games')}>Start one</button>.</div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
                    {activeGames.map((game) => {
                      const IconComp = Gamepad2;
                      return (
                        <ItemCard
                          key={game.id}
                          size="lg"
                          environment={game.gameType}
                          showEnvironmentArt
                          icon={<IconComp className="h-6 w-6 text-primary" />}
                          title={activeGamesService.getGameTypeDisplay(game.gameType)}
                          description={game.isPlayground ? 'Practice game' : 'Competitive match'}
                          headerBadge={<Badge className={activeGamesService.getStatusColor(game.matchmakingStatus)}>{activeGamesService.getStatusDisplay(game.matchmakingStatus)}</Badge>}
                          actions={
                            <div className="flex gap-2">
                              <Button variant="outline" onClick={() => navigate(activeGamesService.getGameUrl(game))}><Eye className="h-4 w-4 mr-2" /> Watch</Button>
                            </div>
                          }
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Latest 5 Historical Games */}
          <div className="w-full xl:w-80 xl:flex-shrink-0">
            <div className="p-4 sm:p-6 bg-card border rounded-xl flex flex-col h-[400px]">
              <h3 className="text-foreground text-lg sm:text-xl font-semibold mb-4 sm:mb-6">Latest Games</h3>
              {loadingGames ? (
                <div className="flex items-center justify-center flex-1"><div className="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-brand-orange" /></div>
              ) : historyGames.length === 0 ? (
                <div className="text-sm text-muted-foreground">No recent games.</div>
              ) : (
                <div className="space-y-3 sm:space-y-4 overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">
                  {historyGames.map((g) => (
                    <div key={g.id} className="flex items-center gap-3 py-2 sm:py-3 px-4 sm:px-5 rounded-lg">
                      <div className="w-2 h-2 rounded-full flex-shrink-0 bg-muted-foreground/40"></div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{activeGamesService.getGameTypeDisplay(g.gameType)}</p>
                        <p className="text-xs text-muted-foreground">{g.finishedAt ? new Date(g.finishedAt).toLocaleString() : '—'}</p>
                      </div>
                      <Button variant="link" size="sm" className="text-xs flex-shrink-0 p-0 h-auto" onClick={() => navigate(`/games/${g.gameType}/${g.id}/replay`)}>
                        <HistoryIcon className="h-3 w-3 mr-1" /> Replay
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        </div>
      </div>

      {/* Matchmaking Modal */}
      {selectedGameType && (
        <MatchmakingModal
          open={matchmakingOpen}
          onOpenChange={setMatchmakingOpen}
          gameType={selectedGameType.id}
          gameTypeName={selectedGameType.name}
        />
      )}
    </PageBackground>
  );
};
