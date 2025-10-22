/**
 * Games Management page for viewing active games and game history.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/common/utility/EmptyState';
import { StatsCarousel } from '@/components/common/utility/StatsCarousel';
import type { StatItem } from '@/components/common/utility/StatsCarousel';

import { SearchAndViewSelector } from '@/components/common/utility/SearchAndViewSelector';
import { usePersistentView } from '@/components/common/utility/ViewSelector';
import { ActionTable } from '@/components/common/tables/ActionTable';
import { ItemCard } from '@/components/common/cards/ItemCard';
import { EnvironmentBackground } from '@/components/art/EnvironmentBackground';
import { ConfirmDialog } from '@/components/common/dialogs/ConfirmDialog';
import { toast } from 'sonner';
import {
  Play,
  Eye,
  Users,
  Clock,
  Gamepad2,
  AlertCircle,
  RefreshCw,
  History,
  Activity,
  UserMinus,
} from 'lucide-react';
import {
  activeGamesService,
  type ActiveGame,
  type GameHistory,
  type GameStats,
  type UnifiedGame,
} from '@/services/activeGamesService';
import { gameMatchingApi } from '@/services/gameMatchingApi';
import { MatchmakingModal } from '@/components/games/MatchmakingModal';
import { getAllGames, type GameConfig } from '@/config/gameConfig';
import { getAvailableGameEnvironments } from '@/services/agentsService';

const GamesManagement: React.FC = () => {
  const [activeGames, setActiveGames] = useState<ActiveGame[]>([]);
  const [gameHistory, setGameHistory] = useState<GameHistory[]>([]);
  const [filteredGames, setFilteredGames] = useState<UnifiedGame[]>([]);
  const [filteredAvailableGames, setFilteredAvailableGames] = useState<GameConfig[]>(getAllGames());
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewType, setViewType] = usePersistentView('games-management', 'grid');

  const [stats, setStats] = useState<GameStats>({
    totalActive: 0,
    waitingForPlayers: 0,
    inProgress: 0,
    playgrounds: 0,
    totalHistory: 0,
    finishedGames: 0,
    cancelledGames: 0,
  });
  const [leaveGameConfirm, setLeaveGameConfirm] = useState<UnifiedGame | null>(null);
  const [matchmakingOpen, setMatchmakingOpen] = useState(false);
  const [selectedGame, setSelectedGame] = useState<GameConfig | null>(null);
  const navigate = useNavigate();

  const loadActiveGames = async () => {
    try {
      setLoading(true);
      const games = await activeGamesService.getActiveGames();
      setActiveGames(games);
    } catch (error) {
      console.error('Failed to load active games:', error);
      toast.error('Failed to load active games');
    } finally {
      setLoading(false);
    }
  };

  const loadGameHistory = async () => {
    try {
      const historyResponse = await activeGamesService.getGameHistory();
      setGameHistory(historyResponse.games);
    } catch (error) {
      console.error('Failed to load game history:', error);
      toast.error('Failed to load game history');
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([loadActiveGames(), loadGameHistory()]);
      setLoading(false);
    };
    loadData();
  }, []);

  // Merge and filter games whenever active games or history changes
  useEffect(() => {
    const merged = activeGamesService.mergeAndSortGames(activeGames, gameHistory);

    // Filter by available environments
    const availableEnvs = getAvailableGameEnvironments();
    const envFiltered = merged.filter((game) =>
      availableEnvs.includes(game.gameType as any)
    );

    // Apply search filter
    const filtered = envFiltered.filter((game) =>
      (game.gameType?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
      (activeGamesService.getStatusDisplay(game.matchmakingStatus)?.toLowerCase().includes(searchQuery.toLowerCase()) || false)
    );
    setFilteredGames(filtered);

    // Filter available games
    const allGames = getAllGames()
      .sort((a, b) => {
        // Sort by status: available games first, then coming soon
        if (a.status === 'available' && b.status === 'coming_soon') return -1;
        if (a.status === 'coming_soon' && b.status === 'available') return 1;
        return 0;
      });

    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      setFilteredAvailableGames(allGames);
    } else {
      const filteredAvailable = allGames.filter((game) =>
        game.title.toLowerCase().includes(q) ||
        game.description.toLowerCase().includes(q) ||
        game.id.toLowerCase().includes(q)
      );
      setFilteredAvailableGames(filteredAvailable);
    }
  }, [activeGames, gameHistory, searchQuery]);

  useEffect(() => {
    setStats(activeGamesService.getGameStats(activeGames, gameHistory));
  }, [activeGames, gameHistory]);

  const handleWatchGame = async (game: UnifiedGame) => {
    try {
      const url = activeGamesService.getGameUrl(game);
      navigate(url);
    } catch (error) {
      console.error('Failed to watch game:', error);
      toast.error('Failed to watch game');
    }
  };

  const handleLeaveGame = (game: UnifiedGame) => {
    setLeaveGameConfirm(game);
  };

  const confirmLeaveGame = async () => {
    if (!leaveGameConfirm) return;

    const gameToLeave = leaveGameConfirm;

    // Optimistically remove from active games
    setActiveGames(prev => prev.filter(g => g.id !== gameToLeave.id));
    setFilteredGames(prev => prev.filter(g => g.id !== gameToLeave.id));

    // Close dialog
    setLeaveGameConfirm(null);

    try {
      await gameMatchingApi.leaveMatchmaking(gameToLeave.id);
      toast.success('Left game successfully');

      // Reload to get updated stats and ensure consistency
      await Promise.all([loadActiveGames(), loadGameHistory()]);
    } catch (error) {
      console.error('Failed to leave game:', error);
      toast.error('Failed to leave game');

      // Revert optimistic update on error
      await loadActiveGames();
    }
  };

  const handleReplayGame = (game: UnifiedGame) => {
    if (!game.hasEvents) {
      toast.error('This game cannot be replayed - no events recorded');
      return;
    }
    // Navigate to the replay page instead of showing modal
    navigate(`/games/${game.gameType}/${game.id}/replay`);
  };

  const handleGameSelect = (game: GameConfig) => {
    if (game.status === 'available') {
      setSelectedGame(game);
      setMatchmakingOpen(true);
    }
  };

  const getGameIcon = (gameType: string) => {
    const gameConfig = getAllGames().find(g => g.id === gameType);
    return gameConfig?.icon || Gamepad2;
  };

  const statsData: StatItem[] = [
    {
      icon: <Activity className="h-5 w-5 sm:h-6 sm:w-6 text-brand-teal" />,
      label: "Active",
      value: stats.totalActive.toString(),
      description: "Waiting + In Progress",
      variant: "teal",
    },
    {
      icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-brand-orange" />,
      label: "Waiting",
      value: stats.waitingForPlayers.toString(),
      description: "Waiting for players",
      variant: "orange",
    },
    {
      icon: <Play className="h-5 w-5 sm:h-6 sm:w-6 text-brand-mint" />,
      label: "In Progress",
      value: stats.inProgress.toString(),
      description: "Games started",
      variant: "mint",
    },
    {
      icon: <History className="h-5 w-5 sm:h-6 sm:w-6 text-purple-500" />,
      label: "History",
      value: stats.totalHistory.toString(),
      description: "Completed games",
      variant: "purple",
    }
  ];

  return (
    <div className="w-full space-y-8 p-6 lg:p-8">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header */}
        <div className="relative mb-6 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="games" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2">
                Play
              </h1>
              <p className="hidden sm:block text-muted-foreground text-lg">
                Monitor your active games and replay completed matches
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={loadActiveGames}
                disabled={loading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>
        </div>

        {/* Stats Carousel */}
        <StatsCarousel stats={statsData} />

        {/* Search and View Toggle - Before Available Games */}
        <SearchAndViewSelector
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Search games..."
          viewType={viewType}
          onViewChange={setViewType}
        />

        {/* Available Games Section - Filtered based on search */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Gamepad2 className="h-5 w-5" /> Available Games
          </h2>
          {filteredAvailableGames.length === 0 ? (
            <EmptyState
              icon={<Gamepad2 className="h-12 w-12" />}
              title="No games found"
              description={`No games match "${searchQuery}". Try a different search term.`}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6 justify-center">
              {filteredAvailableGames.map((game) => {
              const isAvailable = game.status === 'available';
              return (
                <ItemCard
                  key={game.id}
                  size="lg"
                  environment={game.id}
                  showEnvironmentArt={!game.image}
                  backgroundImage={game.image}
                  title={game.title}
                  description={game.description}
                  headerBadge={
                    <Badge variant={isAvailable ? 'default' : 'secondary'} className="mt-1">
                      {isAvailable ? 'Available' : 'Coming Soon'}
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
                      isAvailable ? (
                        <Button
                          size="lg"
                          className="w-full rounded-md bg-brand-teal hover:bg-brand-teal/90 text-base font-semibold"
                          data-testid={`play-game-button-${game.id}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleGameSelect(game);
                          }}
                        >
                          Play
                        </Button>
                      ) : (
                        <Button size="lg" className="w-full rounded-md text-base" variant="secondary" disabled data-testid={`coming-soon-button-${game.id}`}>Coming Soon</Button>
                      )
                    }
                    clickable={isAvailable}
                    onClick={() => isAvailable && handleGameSelect(game)}
                  />
              );
            })}
            </div>
          )}
        </div>

        {/* Main Content */}
        {/* Mobile - Single unified table */}
        <div className="md:hidden">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5" /> My Games ({filteredGames.length})
          </h2>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
          ) : filteredGames.length === 0 ? (
            <EmptyState
              icon={searchQuery ? <AlertCircle className="h-12 w-12" /> : <Gamepad2 className="h-12 w-12" />}
              title={searchQuery ? "No games found" : "No games"}
              description={
                searchQuery
                  ? `No games match "${searchQuery}". Try a different search term.`
                  : "You don't have any games yet."
              }
            />
          ) : (
            <ActionTable
              data={filteredGames}
              loading={loading}
              emptyMessage="No games found"
              minWidth={360}
              defaultSortKey="isActive"
              defaultSortDirection="desc"
              columns={[
                {
                  key: 'game',
                  header: 'Game',
                  className: 'align-top',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    return activeGamesService.getGameTypeDisplay(a.gameType).localeCompare(
                      activeGamesService.getGameTypeDisplay(b.gameType)
                    );
                  },
                  render: (game: UnifiedGame) => {
                    const Icon = getGameIcon(game.gameType);
                    return (
                      <div className="flex items-start gap-3">
                        <div className="bg-primary/10 text-primary flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 space-y-1">
                          <p className="text-sm font-semibold text-foreground">
                            {activeGamesService.getGameTypeDisplay(game.gameType)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {game.isPlayground ? 'Practice game' : 'Competitive match'}
                          </p>
                          <div className="flex items-center gap-2 flex-wrap">
                            {game.isActive ? (
                              // Show matchmaking status for active games
                              <Badge className={activeGamesService.getStatusColor(game.matchmakingStatus)} variant="outline">
                                {activeGamesService.getStatusDisplay(game.matchmakingStatus)}
                              </Badge>
                            ) : null}
                            {game.gameType === 'chess' && game.userColor && (
                              <Badge variant="secondary" className="capitalize">
                                {game.userColor}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  }
                },
                {
                  key: 'status',
                  header: 'Status',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    // Active games first
                    if (a.isActive && !b.isActive) return -1;
                    if (!a.isActive && b.isActive) return 1;
                    return 0;
                  },
                  render: (game: UnifiedGame) => (
                    <Badge variant={game.isActive ? 'default' : 'secondary'}>
                      {game.isActive ? 'Active' : 'Finished'}
                    </Badge>
                  )
                },
                {
                  key: 'agent',
                  header: 'Agent',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    const aName = a.userAgentName || '';
                    const bName = b.userAgentName || '';
                    return aName.localeCompare(bName);
                  },
                  render: (game: UnifiedGame) => (
                    <span className="text-sm text-foreground">
                      {game.userAgentName || 'N/A'}
                    </span>
                  )
                },
                {
                  key: 'date',
                  header: 'Date',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    const aDate = new Date(a.finishedAt || a.startedAt || a.createdAt || 0).getTime();
                    const bDate = new Date(b.finishedAt || b.startedAt || b.createdAt || 0).getTime();
                    return bDate - aDate;
                  },
                  render: (game: UnifiedGame) => {
                    const date = game.finishedAt || game.startedAt || game.createdAt;
                    return (
                      <span className="text-sm text-muted-foreground">
                        {date ? new Date(date).toLocaleDateString() : 'N/A'}
                      </span>
                    );
                  }
                }
              ]}
              actions={[
                {
                  label: 'Watch',
                  icon: <Eye className="h-4 w-4" />,
                  onClick: handleWatchGame,
                  disabled: (game: UnifiedGame) => !game.isActive || !activeGamesService.canWatchGame(game),
                  variant: 'outline'
                },
                {
                  label: 'Leave',
                  icon: <UserMinus className="h-4 w-4" />,
                  onClick: handleLeaveGame,
                  disabled: (game: UnifiedGame) => !game.isActive,
                  variant: 'destructive'
                },
                {
                  label: 'Replay',
                  icon: <History className="h-4 w-4" />,
                  onClick: handleReplayGame,
                  disabled: (game: UnifiedGame) => game.isActive || !game.hasEvents,
                  variant: 'outline'
                }
              ]}
            />
          )}
        </div>

        {/* Desktop - Single unified table */}
        <div className="hidden md:block">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5" /> My Games ({filteredGames.length})
          </h2>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
          ) : filteredGames.length === 0 ? (
            <EmptyState
              icon={<Gamepad2 className="h-12 w-12" />}
              title="No games"
              description="You don't have any games yet."
            />
          ) : (
            <ActionTable
              data={filteredGames}
              loading={loading}
              emptyMessage="No games found"
              minWidth={640}
              defaultSortKey="isActive"
              defaultSortDirection="desc"
              columns={[
                {
                  key: 'game',
                  header: 'Game',
                  className: 'align-top',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    return activeGamesService.getGameTypeDisplay(a.gameType).localeCompare(
                      activeGamesService.getGameTypeDisplay(b.gameType)
                    );
                  },
                  render: (game: UnifiedGame) => {
                    const Icon = getGameIcon(game.gameType);
                    return (
                      <div className="flex items-start gap-3">
                        <div className="bg-primary/10 text-primary flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 space-y-1">
                          <p className="text-sm font-semibold text-foreground">
                            {activeGamesService.getGameTypeDisplay(game.gameType)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {game.isPlayground ? 'Practice game' : 'Competitive match'}
                          </p>
                          <div className="flex items-center gap-2 flex-wrap">
                            {game.isActive ? (
                              // Show matchmaking status for active games
                              <Badge className={activeGamesService.getStatusColor(game.matchmakingStatus)} variant="outline">
                                {activeGamesService.getStatusDisplay(game.matchmakingStatus)}
                              </Badge>
                            ) : null}
                            {game.gameType === 'chess' && game.userColor && (
                              <Badge variant="secondary" className="capitalize">
                                {game.userColor}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  }
                },
                {
                  key: 'status',
                  header: 'Status',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    // Active games first
                    if (a.isActive && !b.isActive) return -1;
                    if (!a.isActive && b.isActive) return 1;
                    return 0;
                  },
                  render: (game: UnifiedGame) => (
                    <Badge variant={game.isActive ? 'default' : 'secondary'}>
                      {game.isActive ? 'Active' : 'Finished'}
                    </Badge>
                  )
                },
                {
                  key: 'players',
                  header: 'Players',
                  sortable: true,
                  render: (game: UnifiedGame) => (
                    <span className="text-sm text-muted-foreground">
                      {game.currentPlayers}/{game.maxPlayers}
                    </span>
                  )
                },
                {
                  key: 'agent',
                  header: 'Agent',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    const aName = a.userAgentName || '';
                    const bName = b.userAgentName || '';
                    return aName.localeCompare(bName);
                  },
                  render: (game: UnifiedGame) => (
                    <span className="text-sm text-foreground">
                      {game.userAgentName || 'N/A'}
                    </span>
                  )
                },
                {
                  key: 'result',
                  header: 'Result',
                  render: (game: UnifiedGame) => {
                    if (!game.userResult) return <span className="text-sm text-muted-foreground">-</span>;

                    const resultConfig = {
                      won: { label: 'Won', className: 'bg-green-100 text-green-800 border-green-200' },
                      lost: { label: 'Lost', className: 'bg-red-100 text-red-800 border-red-200' },
                      draw: { label: 'Draw', className: 'bg-gray-100 text-gray-800 border-gray-200' },
                      placed: { label: 'Placed', className: 'bg-blue-100 text-blue-800 border-blue-200' },
                    };

                    const config = resultConfig[game.userResult];
                    return config ? <Badge className={config.className}>{config.label}</Badge> : <span className="text-sm text-muted-foreground">-</span>;
                  }
                },
                {
                  key: 'date',
                  header: 'Date',
                  sortable: true,
                  sortFn: (a: UnifiedGame, b: UnifiedGame) => {
                    const aDate = new Date(a.finishedAt || a.startedAt || a.createdAt || 0).getTime();
                    const bDate = new Date(b.finishedAt || b.startedAt || b.createdAt || 0).getTime();
                    return bDate - aDate;
                  },
                  render: (game: UnifiedGame) => {
                    const date = game.finishedAt || game.startedAt || game.createdAt;
                    return (
                      <span className="text-sm text-muted-foreground">
                        {date ? new Date(date).toLocaleDateString() : 'N/A'}
                      </span>
                    );
                  }
                }
              ]}
              actions={[
                {
                  label: 'Watch',
                  icon: <Eye className="h-4 w-4" />,
                  onClick: handleWatchGame,
                  disabled: (game: UnifiedGame) => !game.isActive || !activeGamesService.canWatchGame(game),
                  variant: 'outline'
                },
                {
                  label: 'Leave',
                  icon: <UserMinus className="h-4 w-4" />,
                  onClick: handleLeaveGame,
                  disabled: (game: UnifiedGame) => !game.isActive,
                  variant: 'destructive'
                },
                {
                  label: 'Replay',
                  icon: <History className="h-4 w-4" />,
                  onClick: handleReplayGame,
                  disabled: (game: UnifiedGame) => game.isActive || !game.hasEvents,
                  variant: 'outline'
                }
              ]}
            />
          )}
        </div>

      </div>

      <ConfirmDialog
        open={!!leaveGameConfirm}
        onOpenChange={(open) => !open && setLeaveGameConfirm(null)}
        title="Leave Game?"
        description={`Are you sure you want to leave this ${leaveGameConfirm ? activeGamesService.getGameTypeDisplay(leaveGameConfirm.gameType) : 'game'}? You will no longer be part of this match.`}
        confirmText="Leave Game"
        cancelText="Cancel"
        onConfirm={confirmLeaveGame}
        variant="destructive"
      />

      {/* Matchmaking Modal */}
      {selectedGame && (
        <MatchmakingModal
          open={matchmakingOpen}
          onOpenChange={setMatchmakingOpen}
          gameType={selectedGame.id}
          gameTypeName={selectedGame.title}
        />
      )}
    </div>
  );
};

export default GamesManagement;