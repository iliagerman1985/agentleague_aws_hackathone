import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { agentsService, type AgentResponse, GameEnvironment, getGameEnvironmentMetadata, getAvailableGameEnvironments } from "@/services/agentsService";
import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem } from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/common/utility/EmptyState";
import { Badge } from "@/components/ui/badge";
import { StatsCarousel } from "@/components/common/utility/StatsCarousel";
import type { StatItem } from "@/components/common/utility/StatsCarousel";

import { ItemCard } from "@/components/common/cards/ItemCard";
import { getEnvironmentTheme } from "@/lib/environmentThemes";
import { Plus, Search, Bot, Zap, Pencil, Trash2, Clock, Calendar, Play } from "lucide-react";
import { type AgentId } from "@/types/ids";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { AgentProfileModal } from "@/components/common/agent/AgentProfileModal";
import { useAgentProfile } from "@/hooks/useAgentProfile";
import { MatchmakingModal } from "@/components/games/MatchmakingModal";

export const AgentListPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<AgentId | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const { selectedAgentId, isProfileOpen, showAgentProfile, closeAgentProfile } = useAgentProfile();

  // Matchmaking modal state
  const [matchmakingOpen, setMatchmakingOpen] = useState(false);
  const [selectedAgentForPlay, setSelectedAgentForPlay] = useState<AgentResponse | null>(null);

  const [envFilter, setEnvFilter] = useState<GameEnvironment | null>(() => {
    try {
      const stored = localStorage.getItem("env-filter-preference-agents");
      return stored && stored !== "all" ? (stored as GameEnvironment) : null;
    } catch {
      return null;
    }
  });
  const handleEnvChange = React.useCallback((v: GameEnvironment | null) => {
    setEnvFilter(v);
    try {
      localStorage.setItem("env-filter-preference-agents", v ?? "all");
    } catch {
      // ignore storage errors
    }
  }, []);


  useEffect(() => {
    setLoading(true);
    agentsService
      .list(envFilter ?? undefined)
      .then(setAgents)
      .finally(() => setLoading(false));
  }, [envFilter]);

  const onConfirmDelete = async () => {
    if (!deleteId) return;
    await agentsService.delete(deleteId);
    setAgents(await agentsService.list(envFilter ?? undefined));
    setDeleteId(null);
  };

  // Filter agents based on search query and available environments
  const filteredAgents = agents.filter(agent => {
    // Get available environments to filter by
    const availableEnvs = getAvailableGameEnvironments();
    const isAgentEnvAvailable = availableEnvs.includes(agent.gameEnvironment);

    // Show agent only if its environment is available or if a specific filter is applied
    const showAgent = envFilter ? agent.gameEnvironment === envFilter : isAgentEnvAvailable;

    return showAgent && (
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (agent.description && agent.description.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  });

  const formatGameEnvironment = (environment: GameEnvironment) => {
    try {
      // Lazy import to avoid circular issues if any; vite handles dynamic import
      return getGameEnvironmentMetadata(environment).displayName;
    } catch {
      const human = String(environment).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      return human;
    }
  };

  // Handler for playing an agent
  const handlePlayAgent = (agent: AgentResponse) => {
    setSelectedAgentForPlay(agent);
    setMatchmakingOpen(true);
  };

  // Stats for header cards
  const totalAgents = agents.length;
  const activeAgents = agents.filter(a => a.isActive).length;
  const recentlyUpdated = agents.filter(a => {
    const updatedDate = new Date(a.updatedAt);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return updatedDate > weekAgo;
  }).length;

  // Stats data for the carousel
  const statsData: StatItem[] = [
    {
      icon: <Bot className="h-5 w-5 sm:h-6 sm:w-6 text-purple-500" />,
      label: "Total Agents",
      value: totalAgents.toString(),
      description: "AI agents created",
      variant: "purple",
    },
    {
      icon: <Zap className="h-5 w-5 sm:h-6 sm:w-6 text-yellow-500" />,
      label: "Active",
      value: activeAgents.toString(),
      description: "Currently active",
      variant: "yellow",
    },
    {
      icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-blue-500" />,
      label: "Recently Updated",
      value: recentlyUpdated.toString(),
      description: "Updated this week",
      variant: "blue",
    },
    {
      icon: <Calendar className="h-5 w-5 sm:h-6 sm:w-6 text-green-500" />,
      label: "This Week",
      value: recentlyUpdated.toString(),
      description: "New updates",
      variant: "green",
    }
  ];


  return (
    <div className="w-full space-y-8 p-6 lg:p-8" data-testid="agent-list-page">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header - matching the home example */}
        <div className="relative mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6" data-testid="agent-list-header">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="agents" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal" data-testid="agent-list-title">My Agents</h1>
              <p className="hidden sm:block text-muted-foreground text-lg" data-testid="agent-list-subtitle">
                Create and manage your AI agents for different game environments
              </p>
            </div>
          </div>
        </div>

        {/* Stats Carousel */}
        <StatsCarousel stats={statsData} />

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="search-input"
            />
          </div>
          <div className="flex items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" data-testid="agent-env-filter">
                  {envFilter ? `Environment: ${formatGameEnvironment(envFilter)}` : "Environment: All"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuRadioGroup
                  value={envFilter ?? "all"}
                  onValueChange={(v) => handleEnvChange(v === "all" ? null : (v as GameEnvironment))}
                >
                  <DropdownMenuRadioItem value="all">All</DropdownMenuRadioItem>
                  {getAvailableGameEnvironments().map((env) => (
                    <DropdownMenuRadioItem key={env} value={env}>
                      {formatGameEnvironment(env as GameEnvironment)}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="brand-primary" onClick={() => navigate('/agents/new')} data-testid="create-agent-button">
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline ml-2">Create Agent</span>
            </Button>
          </div>
        </div>

        {filteredAgents.length === 0 && !loading ? (
          searchQuery ? (
            <EmptyState
              icon={<Search className="h-12 w-12" />}
              title="No agents found"
              description={`No agents match "${searchQuery}". Try a different search term.`}
              data-testid="agent-list-empty-search"
            />
          ) : (
            <EmptyState
              icon={<Bot className="h-12 w-12" />}
              title="No agents yet"
              description="You haven't created any agents yet. Create your first agent to get started with automated gameplay."
              action={{
                label: "Create your first agent",
                onClick: () => navigate("/agents/new")
              }}
              data-testid="agent-list-empty-state"
            />
          )
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6 justify-center" data-testid="agent-list-grid-view">
            {filteredAgents.map((agent) => {
              const theme = getEnvironmentTheme(agent.gameEnvironment);

              return (
                <ItemCard
                  key={agent.id}
                  size="lg"
                  title={agent.name}
                  description={agent.description && agent.description.trim().length > 0 ? agent.description : "No description provided"}
                  environment={agent.gameEnvironment}
                  showEnvironmentArt={!agent.avatarUrl}
                  backgroundImage={agent.avatarUrl ?? undefined}
                  backgroundImageOpacity={agent.avatarUrl ? 0.3 : 0.12}
                  backgroundImageGrayscale={true}
                  onClick={() => showAgentProfile(agent.id)}
                  clickable={true}
                  belowTitle={
                    <div className="flex items-center gap-1 whitespace-nowrap text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      <span>{new Date(agent.updatedAt).toLocaleString(undefined, { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  }
                  bottomLeft={
                    <Badge variant="default" className="flex items-center gap-1.5 px-3 py-1 text-sm font-semibold bg-primary/90 hover:bg-primary">
                      {React.createElement(theme.icon, { className: `h-5 w-5 ${theme.iconColor}` })}
                      <span>{formatGameEnvironment(agent.gameEnvironment)}</span>
                    </Badge>
                  }
                  actions={
                    <>
                      <Button
                        variant="default"
                        size="sm"
                        className="bg-brand-teal hover:bg-brand-teal/90"
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePlayAgent(agent);
                        }}
                        data-testid={`play-agent-button-${agent.id}`}
                      >
                        <Play className="h-4 w-4 mr-2" />
                        Play
                      </Button>
                      <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/agents/${agent.id}`); }} data-testid={`edit-agent-button-${agent.id}`}>
                        <Pencil className="h-4 w-4 mr-2" />
                        Edit
                      </Button>
                      <Button variant="destructive" size="sm" onClick={(e) => { e.stopPropagation(); setDeleteId(agent.id); }} data-testid={`delete-agent-button-${agent.id}`}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </Button>
                    </>
                  }
                />
              );
            })}
          </div>
        )}

        <ConfirmDialog
          open={!!deleteId}
          title="Delete agent?"
          description="This action cannot be undone. All agent versions and statistics will be permanently deleted."
          onOpenChange={() => setDeleteId(null)}
          onConfirm={onConfirmDelete}
          data-testid="agent-delete-confirm-dialog"
        />

        <AgentProfileModal
          agentId={selectedAgentId}
          open={isProfileOpen}
          onOpenChange={closeAgentProfile}
        />

        {/* Matchmaking Modal */}
        {selectedAgentForPlay && (
          <MatchmakingModal
            open={matchmakingOpen}
            onOpenChange={setMatchmakingOpen}
            gameType={selectedAgentForPlay.gameEnvironment}
            gameTypeName={formatGameEnvironment(selectedAgentForPlay.gameEnvironment)}
            preSelectedAgentId={selectedAgentForPlay.id}
            autoStart={true}
          />
        )}
      </div>
    </div>
  );
};

export default AgentListPage;
