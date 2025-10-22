import React, { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/utility/EmptyState";
import { usePersistentView } from "@/components/common/utility/ViewSelector";
import { SearchAndViewSelector } from "@/components/common/utility/SearchAndViewSelector";
import { StatsCarousel } from "@/components/common/utility/StatsCarousel";
import { ActionTable } from "@/components/common/tables/ActionTable";
import { ItemCard } from "@/components/common/cards/ItemCard";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { MatchmakingModal } from "@/components/games/MatchmakingModal";
import { Users, Clock, Trophy, Search, Play, Spade } from "lucide-react";
import { getAllGames, type GameConfig } from "@/config/gameConfig";

export const Games: React.FC = () => {
  const [viewType, setViewType] = usePersistentView('games', 'grid');
  const [searchQuery, setSearchQuery] = useState("");
  const [matchmakingOpen, setMatchmakingOpen] = useState(false);
  const [selectedGame, setSelectedGame] = useState<GameConfig | null>(null);

  const gameOptions = getAllGames().sort((a, b) => {
    // Sort by status: available games first, then coming soon
    if (a.status === 'available' && b.status === 'coming_soon') return -1;
    if (a.status === 'coming_soon' && b.status === 'available') return 1;
    return 0;
  });

  const filteredGames = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    let games = gameOptions;

    // Filter out poker (coming soon games) when showing all games
    games = games.filter(g => g.status === 'available');

    if (!q) return games;
    return games.filter((g) =>
      g.title.toLowerCase().includes(q) || g.description.toLowerCase().includes(q)
    );
  }, [searchQuery, gameOptions]);

  const totalGames = gameOptions.filter(g => g.status === 'available').length;
  const availableCount = gameOptions.filter(g => g.status === 'available').length;
  const comingSoonCount = 0; // Hide coming soon games from the main games page

  // Stats data for the carousel
  const statsData = [
    {
      icon: <Spade className="h-5 w-5 sm:h-6 sm:w-6 text-red-500" />,
      label: "Total Games",
      value: totalGames.toString(),
      description: "Available game types"
    },
    {
      icon: <Trophy className="h-5 w-5 sm:h-6 sm:w-6 text-yellow-500" />,
      label: "Available",
      value: availableCount.toString(),
      description: "Ready to play"
    },
    {
      icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-blue-500" />,
      label: "Coming Soon",
      value: comingSoonCount.toString(),
      description: "In development"
    }
  ];

  const handleGameSelect = (game: GameConfig) => {
    if (game.status === 'available') {
      setSelectedGame(game);
      setMatchmakingOpen(true);
    }
  };

  const getTruncated = (value: string, length: number) => {
    if (!value) {
      return value;
    }
    if (value.length <= length) {
      return value;
    }
    return `${value.slice(0, Math.max(0, length - 1))}…`;
  };

  return (
    <div className="w-full space-y-8 p-6 lg:p-8" data-testid="games-page">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header - consistent with Agent Editor */}
        <div className="relative mb-6 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6" data-testid="games-header">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="games" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal" data-testid="games-title">Games</h1>
              <p className="hidden sm:block text-muted-foreground text-lg" data-testid="games-subtitle">Browse and simulate games</p>
            </div>
          </div>
        </div>

      {/* Stats Carousel */}
      <StatsCarousel stats={statsData} />

      {/* Search + View toggle (match Tools/Agents) */}
      <SearchAndViewSelector
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search games..."
        viewType={viewType}
        onViewChange={setViewType}
      />

      {/* Games content */}
      {filteredGames.length === 0 ? (
        <EmptyState
          icon={<Search className="h-12 w-12" />}
          title="No games found"
          description={searchQuery ? `No games match "${searchQuery}". Try a different search term.` : "No games available yet."}
          data-testid="games-empty-state"
        />
      ) : viewType === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6 justify-center" data-testid="games-grid-view">
          {filteredGames.map((game) => {
            const isAvailable = game.status === 'available';
            return (
              <ItemCard
              		        size="lg"
                environment={game.id}
                showEnvironmentArt={!game.image}
                backgroundImage={game.image}
                key={game.id}
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
      ) : (
        <ActionTable
          data={filteredGames}
          loading={false}
          emptyMessage="No games found"
          minWidth={520}
          columns={[
            {
              key: 'title',
              header: 'Game',
              className: 'align-top',
              render: (g: GameConfig) => (
                <div className="flex items-start gap-3">
                  <div className={(g.status === 'available' ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground') + ' flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full'}>
                    {React.createElement(g.icon, { className: 'h-4 w-4' })}
                  </div>
                  <div className="min-w-0 space-y-1">
                    <p className="text-sm font-semibold text-foreground sm:text-base" title={g.title}>
                      <span className="sm:hidden">{getTruncated(g.title, 26)}</span>
                      <span className="hidden sm:inline">{g.title}</span>
                    </p>
                    <p className="text-[11px] text-muted-foreground leading-4 sm:text-xs" title={g.description}>
                      <span className="sm:hidden">{getTruncated(g.description, 44)}</span>
                      <span className="hidden sm:inline">{g.description}</span>
                    </p>
                    <p className="text-[11px] text-muted-foreground sm:hidden">Up to {g.maxPlayers} players · {g.estimatedTime}</p>
                  </div>
                </div>
              )
            },
            {
              key: 'status',
              header: 'Status',
              headerClassName: 'hidden sm:table-cell',
              className: 'hidden sm:table-cell',
              render: (g: GameConfig) => (
                <Badge variant={g.status === 'available' ? 'default' : 'secondary'}>
                  {g.status === 'available' ? 'Available' : 'Coming Soon'}
                </Badge>
              )
            },
            {
              key: 'players',
              header: 'Players',
              headerClassName: 'hidden md:table-cell',
              className: 'hidden md:table-cell',
              render: (g: GameConfig) => (
                <span className="text-sm text-muted-foreground">Up to {g.maxPlayers}</span>
              )
            },
            {
              key: 'time',
              header: 'Est. Time',
              headerClassName: 'hidden md:table-cell',
              className: 'hidden md:table-cell',
              render: (g: GameConfig) => (
                <span className="text-sm text-muted-foreground">{g.estimatedTime}</span>
              )
            }
          ]}
          actions={[
            {
              label: 'Play',
              variant: 'outline',
              icon: <Play className="h-4 w-4" />,
              onClick: (g: GameConfig) => g.status === 'available' && handleGameSelect(g),
              disabled: (g: GameConfig) => g.status !== 'available'
            }
          ]}
          data-testid="games-table-view"
        />
      )}

      </div>

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
}

export default Games;
