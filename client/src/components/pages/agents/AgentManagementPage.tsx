import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Bot,
  Plus,
  Pencil,
  Trash2,
  Zap,
  Clock,
  Calendar,
  Search,
  Wrench,
  Code,
  FlaskConical,
  Beaker,
  TestTube,
  Copy,
  Eye,
  Filter,
  Play
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ConfirmDialog } from '@/components/common/dialogs/ConfirmDialog';
import { EmptyState } from '@/components/common/utility/EmptyState';
import { ItemCard } from '@/components/common/cards/ItemCard';
import { ActionTable } from '@/components/common/tables/ActionTable';
import { DataTable } from '@/components/common/tables/DataTable';
import { StatsCarousel } from '@/components/common/utility/StatsCarousel';
import type { StatItem } from "@/components/common/utility/StatsCarousel";

import { EnvironmentBackground } from '@/components/art/EnvironmentBackground';
import { AgentProfileModal } from '@/components/common/agent/AgentProfileModal';
import { useAgentProfile } from '@/hooks/useAgentProfile';
import { agentsService, type AgentResponse, type GameEnvironment, type TestScenarioResponse, getGameEnvironmentMetadata, getAvailableGameEnvironments } from '@/services/agentsService';
import { toolsService, type Tool } from '@/services/toolsService';
import { useToasts } from '@/components/common/notifications/ToastProvider';
import { MatchmakingModal } from '@/components/games/MatchmakingModal';
import { getEnvironmentTheme } from '@/lib/environmentThemes';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import type { AgentId, ToolId, TestScenarioId } from '@/types/ids';

export const AgentManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { push } = useToasts();

  // Get active tab from URL or default to 'agents'
  const activeTab = searchParams.get('tab') || 'agents';

  const setActiveTab = (tab: string) => {
    setSearchParams({ tab });
  };

  // Agents state
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [deleteAgentId, setDeleteAgentId] = useState<AgentId | null>(null);
  const [agentSearchQuery, setAgentSearchQuery] = useState("");
  const { selectedAgentId, isProfileOpen, showAgentProfile, closeAgentProfile } = useAgentProfile();
  const [agentEnvFilter, setAgentEnvFilter] = useState<GameEnvironment | null>(() => {
    try {
      const stored = localStorage.getItem("env-filter-preference-agents");
      return stored && stored !== "all" ? (stored as GameEnvironment) : null;
    } catch {
      return null;
    }
  });

  // Matchmaking modal state
  const [matchmakingOpen, setMatchmakingOpen] = useState(false);
  const [selectedAgentForPlay, setSelectedAgentForPlay] = useState<AgentResponse | null>(null);

  const handleAgentEnvChange = useCallback((v: GameEnvironment | null) => {
    setAgentEnvFilter(v);
    try {
      localStorage.setItem("env-filter-preference-agents", v ?? "all");
    } catch {
      // ignore storage errors
    }
  }, []);

  // Tools state
  const [tools, setTools] = useState<Tool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [deleteToolId, setDeleteToolId] = useState<ToolId | null>(null);
  const [toolUsage, setToolUsage] = useState<{ agents: { id: string; name: string }[]; agentsCount: number } | null>(null);
  const [toolSearchQuery, setToolSearchQuery] = useState("");
  const [toolEnvironmentFilter, setToolEnvironmentFilter] = useState<GameEnvironment | "all">("all");

  // Tests state
  const [scenarios, setScenarios] = useState<TestScenarioResponse[]>([]);
  const [testsLoading, setTestsLoading] = useState(false);
  const [deleteTestId, setDeleteTestId] = useState<TestScenarioId | null>(null);
  const [testSearch, setTestSearch] = useState("");
  const [testEnvFilter, setTestEnvFilter] = useState<"all" | GameEnvironment>("all");
  const [showSystemScenarios, setShowSystemScenarios] = useState<boolean>(() => {
    const saved = localStorage.getItem("tests-show-system-scenarios");
    return saved !== null ? saved === "true" : true;
  });
  const [testEnvOptions, setTestEnvOptions] = useState<GameEnvironment[]>([]);

  // Load agents
  useEffect(() => {
    setAgentsLoading(true);
    agentsService
      .list(agentEnvFilter ?? undefined)
      .then(setAgents)
      .finally(() => setAgentsLoading(false));
  }, [agentEnvFilter]);

  // Load tools
  useEffect(() => {
    toolsService.list().then(setTools).finally(() => setToolsLoading(false));
  }, []);

  // Load tests
  const loadTests = useCallback(async () => {
    setTestsLoading(true);
    try {
      const list = await agentsService.getTestScenarios({ includeSystem: showSystemScenarios });
      setScenarios(list || []);
    } catch (e: any) {
      push({ title: "Failed to load tests", message: String(e?.message || e), tone: "error" });
    } finally {
      setTestsLoading(false);
    }
  }, [push, showSystemScenarios]);

  useEffect(() => {
    void loadTests();
  }, [loadTests]);

  // Load test env options
  useEffect(() => {
    const run = async () => {
      try {
        const agentsList = await agentsService.list();
        const availableEnvs = getAvailableGameEnvironments();
        const envs = Array.from(new Set(agentsList.map(a => a.gameEnvironment)))
          .filter(env => availableEnvs.includes(env)) as GameEnvironment[];
        setTestEnvOptions(envs);
      } catch {
        setTestEnvOptions([]);
      }
    };
    void run();
  }, []);

  // Save test preferences
  useEffect(() => {
    localStorage.setItem("tests-show-system-scenarios", String(showSystemScenarios));
  }, [showSystemScenarios]);

  // Load tool usage when delete tool is selected
  useEffect(() => {
    if (!deleteToolId) { setToolUsage(null); return; }
    toolsService.usage(deleteToolId)
      .then(setToolUsage)
      .catch(() => setToolUsage({ agents: [], agentsCount: 0 }));
  }, [deleteToolId]);

  // Agent handlers
  const onConfirmDeleteAgent = async () => {
    if (!deleteAgentId) return;
    await agentsService.delete(deleteAgentId);
    setAgents(await agentsService.list(agentEnvFilter ?? undefined));
    setDeleteAgentId(null);
  };

  // Tool handlers
  const onConfirmDeleteTool = async () => {
    if (!deleteToolId) return;
    if (toolUsage && toolUsage.agentsCount > 0) {
      await toolsService.deleteWithDetach(deleteToolId);
    } else {
      await toolsService.delete(deleteToolId);
    }
    setTools(await toolsService.list());
    setDeleteToolId(null);
  };

  // Test handlers
  const duplicateTest = async (row: TestScenarioResponse) => {
    try {
      await agentsService.createTestScenario({
        name: `Copy of ${row.name}`,
        description: row.description || undefined,
        environment: row.environment,
        gameState: row.gameState || {},
        tags: [],
      });
      push({ title: "Duplicated", message: `Created copy of ${row.name}`, tone: "success" });
      void loadTests();
    } catch (e: any) {
      push({ title: "Duplicate failed", message: String(e?.message || e), tone: "error" });
    }
  };

  const handleDeleteTestConfirm = async () => {
    if (!deleteTestId) return;
    try {
      await agentsService.deleteTestScenario(deleteTestId);
      push({ title: "Deleted", message: "Test scenario deleted", tone: "success" });
      setDeleteTestId(null);
      void loadTests();
    } catch (e: any) {
      push({ title: "Delete failed", message: String(e?.message || e), tone: "error" });
      setDeleteTestId(null);
    }
  };

  // Handler for playing an agent
  const handlePlayAgent = (agent: AgentResponse) => {
    setSelectedAgentForPlay(agent);
    setMatchmakingOpen(true);
  };

  // Utility functions
  const getTruncated = (value: string, length: number) => {
    if (!value) return value;
    if (value.length <= length) return value;
    return `${value.slice(0, Math.max(0, length - 1))}…`;
  };

  const formatGameEnvironment = (environment: GameEnvironment) => {
    try {
      return getGameEnvironmentMetadata(environment).displayName;
    } catch {
      return String(environment).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
  };

  const titleize = (s: string) => s.split("_").map(w => w ? (w[0].toUpperCase() + w.slice(1)) : w).join(" ");

  const cleanDescription = (value?: string): string => {
    if (!value) return "";
    return value.replace(/^\s*#+\s*Human-Readable Description\s*/i, "").trim();
  };

  // Filter data
  const filteredAgents = agents.filter(agent => {
    // Filter by available environments
    const availableEnvs = getAvailableGameEnvironments();
    const isAgentEnvAvailable = availableEnvs.includes(agent.gameEnvironment);

    // Filter by search query
    const matchesSearch = agent.name.toLowerCase().includes(agentSearchQuery.toLowerCase()) ||
      (agent.description && agent.description.toLowerCase().includes(agentSearchQuery.toLowerCase()));

    return isAgentEnvAvailable && matchesSearch;
  });

  const filteredTools = tools.filter(tool => {
    // Filter by available environments
    const availableEnvs = getAvailableGameEnvironments();
    const isToolEnvAvailable = availableEnvs.includes(tool.environment as any);

    // Filter by search query
    const matchesSearch = (tool.displayName || "").toLowerCase().includes(toolSearchQuery.toLowerCase());

    // Filter by environment filter
    const matchesEnvFilter = toolEnvironmentFilter === "all"
      ? isToolEnvAvailable
      : tool.environment === toolEnvironmentFilter;

    return matchesSearch && matchesEnvFilter;
  });

  const filteredTests = useMemo(() => {
    const q = testSearch.trim().toLowerCase();
    return scenarios.filter((s) => {
      // Filter by available environments
      const availableEnvs = getAvailableGameEnvironments();
      const isTestEnvAvailable = availableEnvs.includes(s.environment as any);

      // Filter by environment filter
      const matchesEnv = testEnvFilter === "all"
        ? isTestEnvAvailable
        : s.environment === testEnvFilter;

      // Filter by search query
      const matchesSearch = !q || s.name.toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q);

      return matchesEnv && matchesSearch;
    });
  }, [scenarios, testEnvFilter, testSearch]);

  // Stats calculations - only count items from available environments
  const availableEnvs = getAvailableGameEnvironments();

  const agentsInActiveEnvs = agents.filter(a => availableEnvs.includes(a.gameEnvironment));
  const totalAgents = agentsInActiveEnvs.length;
  const activeAgents = agentsInActiveEnvs.filter(a => a.isActive).length;
  const recentlyUpdatedAgents = agentsInActiveEnvs.filter(a => {
    const updatedDate = new Date(a.updatedAt);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return updatedDate > weekAgo;
  }).length;

  const toolsInActiveEnvs = tools.filter(t => availableEnvs.includes(t.environment as any));
  const totalTools = toolsInActiveEnvs.length;
  const recentlyUpdatedTools = toolsInActiveEnvs.filter((tool) => {
    const updatedDate = new Date(tool.updatedAt);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return updatedDate > weekAgo;
  }).length;
  const averageCodeLength = toolsInActiveEnvs.length > 0
    ? Math.round(toolsInActiveEnvs.reduce((sum, tool) => sum + tool.code.length, 0) / toolsInActiveEnvs.length)
    : 0;

  const testsInActiveEnvs = scenarios.filter(s => availableEnvs.includes(s.environment as any));
  const totalTests = testsInActiveEnvs.length;
  const userTests = testsInActiveEnvs.filter(s => !s.isSystem).length;
  const systemTests = testsInActiveEnvs.filter(s => s.isSystem).length;
  const recentlyUpdatedTests = testsInActiveEnvs.filter(s => {
    const updatedDate = new Date(s.updatedAt);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return updatedDate > weekAgo;
  }).length;

  // Stats data
  const agentStatsData: StatItem[] = [
    { icon: <Bot className="h-5 w-5 sm:h-6 sm:w-6 text-purple-500" />, label: "Total Agents", value: totalAgents.toString(), description: "AI agents created", variant: "purple" },
    { icon: <Zap className="h-5 w-5 sm:h-6 sm:w-6 text-yellow-500" />, label: "Active", value: activeAgents.toString(), description: "Currently active", variant: "yellow" },
    { icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-blue-500" />, label: "Recently Updated", value: recentlyUpdatedAgents.toString(), description: "Updated this week", variant: "blue" },
    { icon: <Calendar className="h-5 w-5 sm:h-6 sm:w-6 text-green-500" />, label: "This Week", value: recentlyUpdatedAgents.toString(), description: "New updates", variant: "green" }
  ];

  const toolStatsData: StatItem[] = [
    { icon: <Wrench className="h-5 w-5 sm:h-6 sm:w-6 text-sky-500" />, label: "Total Tools", value: totalTools.toString(), description: "Custom utilities created", variant: "sky" },
    { icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-amber-500" />, label: "Recently Updated", value: recentlyUpdatedTools.toString(), description: "Touched this week", variant: "amber" },
    { icon: <Code className="h-5 w-5 sm:h-6 sm:w-6 text-cyan-500" />, label: "Avg. Size", value: `${averageCodeLength}`, description: "Characters per tool", variant: "cyan" }
  ];

  const testStatsData: StatItem[] = [
    { icon: <TestTube className="h-5 w-5 sm:h-6 sm:w-6 text-cyan-500" />, label: "Total Tests", value: totalTests.toString(), description: "Test scenarios created", variant: "cyan" },
    { icon: <Beaker className="h-5 w-5 sm:h-6 sm:w-6 text-indigo-500" />, label: "User Tests", value: userTests.toString(), description: "Custom scenarios", variant: "indigo" },
    { icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-amber-500" />, label: "System Tests", value: systemTests.toString(), description: "Predefined scenarios", variant: "amber" },
    { icon: <Calendar className="h-5 w-5 sm:h-6 sm:w-6 text-emerald-500" />, label: "This Week", value: recentlyUpdatedTests.toString(), description: "New updates", variant: "emerald" }
  ];

  const toolConfirmText = toolUsage && toolUsage.agentsCount > 0 ? "Remove from agents and delete" : "Delete";
  const toolConfirmTitle = toolUsage && toolUsage.agentsCount > 0 ? "Tool is in use" : "Delete tool?";
  const toolConfirmDescription = toolUsage && toolUsage.agentsCount > 0
    ? `This tool is used by ${toolUsage.agentsCount} agent(s): ${toolUsage.agents.map(a => a.name).join(', ')}. Continuing will remove it from these agents and delete the tool.`
    : "This action cannot be undone.";

  // Test columns for table view
  const testColumns = [
    {
      key: "name",
      header: "Test",
      className: "max-w-[220px]",
      render: (item: TestScenarioResponse) => {
        const theme = getEnvironmentTheme(item.environment);
        return (
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              {React.createElement(theme.icon, { className: `h-4 w-4 ${theme.iconColor}` })}
            </div>
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-foreground sm:text-base" title={item.name}>
                  <span className="sm:hidden">{getTruncated(item.name, 28)}</span>
                  <span className="hidden sm:inline">{item.name}</span>
                </p>
                {item.isSystem && (
                  <Badge className="bg-amber-500/15 text-amber-400 border border-amber-500/20 px-2 py-0 text-[10px] font-medium">
                    System
                  </Badge>
                )}
              </div>
              {item.description && (
                <p className="text-[11px] text-muted-foreground leading-4 sm:text-xs" title={item.description}>
                  <span className="sm:hidden">{getTruncated(item.description, 44)}</span>
                  <span className="hidden sm:inline">{item.description}</span>
                </p>
              )}
              <p className="text-[11px] text-muted-foreground sm:hidden" title={titleize(item.environment)}>
                {titleize(item.environment)}
              </p>
            </div>
          </div>
        );
      },
    },
    {
      key: "environment",
      header: "Environment",
      headerClassName: "hidden sm:table-cell",
      className: "hidden sm:table-cell capitalize text-sm text-muted-foreground",
      render: (item: TestScenarioResponse) => titleize(item.environment),
    },
    {
      key: "updated",
      header: "Updated",
      headerClassName: "hidden md:table-cell",
      className: "hidden md:table-cell text-sm text-muted-foreground",
      render: (item: TestScenarioResponse) => new Date(item.updatedAt).toLocaleDateString(),
    },
    {
      key: "actions",
      header: "",
      headerClassName: "text-right",
      className: "w-0",
      render: (item: TestScenarioResponse) => (
        <div className="flex items-center justify-end gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate(`/tests/${item.id}`)}
            title={item.isSystem ? "View system test" : "Edit test"}
            aria-label={item.isSystem ? "View test" : "Edit test"}
            className="h-9 w-9 sm:w-auto sm:px-3 sm:h-9 justify-center rounded-full sm:rounded-md"
          >
            {item.isSystem ? <Eye className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
            <span className="hidden sm:inline ml-2">{item.isSystem ? "View" : "Edit"}</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => duplicateTest(item)}
            title="Duplicate test"
            aria-label="Duplicate test"
            className="h-9 w-9 sm:w-auto sm:px-3 sm:h-9 justify-center rounded-full sm:rounded-md"
          >
            <Copy className="h-4 w-4" />
            <span className="hidden sm:inline ml-2">Duplicate</span>
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setDeleteTestId(item.id)}
            disabled={item.isSystem}
            title={item.isSystem ? "System tests cannot be deleted" : "Delete test"}
            aria-label={item.isSystem ? "System test" : "Delete test"}
            className="h-9 w-9 sm:w-auto sm:px-3 sm:h-9 justify-center rounded-full sm:rounded-md"
          >
            <Trash2 className="h-4 w-4" />
            <span className="hidden sm:inline ml-2">Delete</span>
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="w-full space-y-8 p-6 lg:p-8" data-testid="agent-management-page">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header */}
        <div className="relative mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="agents" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal">
                Agents
              </h1>
              <p className="hidden sm:block text-muted-foreground text-lg">
                Manage your AI agents, tools, and test scenarios
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 h-14 p-1 bg-transparent border-b border-border/50 rounded-none mb-8">
            <TabsTrigger
              value="agents"
              className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
            >
              <Bot className="h-6 w-6 sm:h-5 sm:w-5 text-cyan-500 group-data-[state=active]:text-primary-foreground" />
              <span className="hidden sm:inline">Agents</span>
            </TabsTrigger>
            <TabsTrigger
              value="tools"
              className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
            >
              <Wrench className="h-6 w-6 sm:h-5 sm:w-5 text-orange-500 group-data-[state=active]:text-primary-foreground" />
              <span className="hidden sm:inline">Tools</span>
            </TabsTrigger>
            <TabsTrigger
              value="tests"
              className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
            >
              <FlaskConical className="h-6 w-6 sm:h-5 sm:w-5 text-green-500 group-data-[state=active]:text-primary-foreground" />
              <span className="hidden sm:inline">Tests</span>
            </TabsTrigger>
          </TabsList>

          {/* Agents Tab */}
          <TabsContent value="agents" className="space-y-6">
            <StatsCarousel stats={agentStatsData} />

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search agents..."
                  value={agentSearchQuery}
                  onChange={(e) => setAgentSearchQuery(e.target.value)}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <div className="flex items-center gap-3">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" data-testid="agent-env-filter">
                      {agentEnvFilter ? `Environment: ${formatGameEnvironment(agentEnvFilter)}` : "Environment: All"}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuRadioGroup
                      value={agentEnvFilter ?? "all"}
                      onValueChange={(v) => handleAgentEnvChange(v === "all" ? null : (v as GameEnvironment))}
                    >
                      <DropdownMenuRadioItem value="all">All</DropdownMenuRadioItem>
                      {getAvailableGameEnvironments().map((env: any) => (
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

            {filteredAgents.length === 0 && !agentsLoading ? (
              agentSearchQuery ? (
                <EmptyState
                  icon={<Search className="h-12 w-12" />}
                  title="No agents found"
                  description={`No agents match "${agentSearchQuery}". Try a different search term.`}
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
                />
              )
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6 justify-center">
                {filteredAgents.map((agent) => {
                  const theme = getEnvironmentTheme(agent.gameEnvironment);

                  return (
                    <ItemCard
                      size="lg"
                      key={agent.id}
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
                          <span>{new Date(agent.updatedAt).toLocaleDateString()}</span>
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
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Play
                          </Button>
                          <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/agents/${agent.id}`); }}>
                            <Pencil className="h-4 w-4 mr-2" />
                            Edit
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); setDeleteAgentId(agent.id); }}
                            disabled={agent.isSystem}
                            title={agent.isSystem ? "System agents cannot be deleted" : "Delete agent"}
                          >
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
          </TabsContent>

          {/* Tools Tab */}
          <TabsContent value="tools" className="space-y-6">
            <StatsCarousel stats={toolStatsData} />

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search tools..."
                  value={toolSearchQuery}
                  onChange={(e) => setToolSearchQuery(e.target.value)}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <div className="flex items-center gap-3">
                <Select value={toolEnvironmentFilter} onValueChange={(value) => setToolEnvironmentFilter(value as GameEnvironment | "all")}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="All environments" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Environments</SelectItem>
                    {getAvailableGameEnvironments().map((env) => (
                      <SelectItem key={env} value={env}>
                        {env === 'chess' ? 'Chess' : env === 'texas_holdem' ? 'Texas Hold\'em' : env}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="brand-primary" onClick={() => navigate('/tools/new')}>
                  <Plus className="h-4 w-4" />
                  <span className="hidden sm:inline ml-2">Create Tool</span>
                </Button>
              </div>
            </div>

            {filteredTools.length === 0 && !toolsLoading ? (
              toolSearchQuery ? (
                <EmptyState
                  icon={<Search className="h-12 w-12" />}
                  title="No tools found"
                  description={`No tools match "${toolSearchQuery}". Try a different search term.`}
                />
              ) : (
                <EmptyState
                  icon={<Plus className="h-12 w-12" />}
                  title="No tools yet"
                  description="You haven't created any tools yet. Create your first tool to get started."
                  action={{
                    label: "Create your first tool",
                    onClick: () => navigate("/tools/new")
                  }}
                />
              )
            ) : (
              <ActionTable
                data={filteredTools}
                loading={toolsLoading}
                emptyMessage="No tools found"
                minWidth={520}
                columns={[
                  {
                    key: "name",
                    header: "Tool",
                    className: "align-middle",
                    render: (tool) => (
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <Code className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 space-y-1">
                          <p className="text-sm font-medium text-foreground sm:text-base sm:leading-5" title={tool.displayName}>
                            <span className="sm:hidden">{getTruncated(tool.displayName, 20)}</span>
                            <span className="hidden sm:inline">{tool.displayName}</span>
                          </p>
                          {tool.description && (
                            <p className="text-[11px] text-muted-foreground leading-4 sm:text-xs" title={cleanDescription(tool.description)}>
                              <span className="sm:hidden">{getTruncated(cleanDescription(tool.description), 30)}</span>
                              <span className="hidden sm:inline">{getTruncated(cleanDescription(tool.description), 60)}</span>
                            </p>
                          )}
                        </div>
                      </div>
                    )
                  },
                  {
                    key: 'environment',
                    header: 'Environment',
                    headerClassName: 'hidden sm:table-cell',
                    className: 'hidden sm:table-cell',
                    render: (tool) => (
                      <Badge variant="outline" className="text-xs">
                        {tool.environment === 'texas_holdem' ? 'Texas Hold\'em' : 'Chess'}
                      </Badge>
                    )
                  },
                  {
                    key: 'codeLength',
                    header: 'Code Size',
                    headerClassName: 'hidden sm:table-cell',
                    className: 'hidden sm:table-cell',
                    render: (tool) => (
                      <span className="text-sm text-muted-foreground">
                        {tool.code.length} chars
                      </span>
                    )
                  },
                  {
                    key: 'status',
                    header: 'Status',
                    headerClassName: 'hidden sm:table-cell',
                    className: 'hidden sm:table-cell',
                    render: (tool) => (
                      <Badge className={
                        tool.validationStatus === 'valid'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : tool.validationStatus === 'pending'
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                            : 'bg-red-500/15 text-red-400 border border-red-500/30'
                      }>
                        {tool.validationStatus.toUpperCase()}
                      </Badge>
                    )
                  },
                  {
                    key: 'updatedAt',
                    header: 'Updated',
                    headerClassName: 'hidden md:table-cell',
                    className: 'hidden md:table-cell',
                    render: (tool) => (
                      <span className="text-sm text-muted-foreground">
                        {new Date(tool.updatedAt).toLocaleDateString()}
                      </span>
                    )
                  }
                ]}
                actions={[
                  {
                    label: 'Edit',
                    variant: 'outline',
                    icon: <Pencil className="h-4 w-4" />,
                    onClick: (tool) => navigate(`/tools/${tool.id}`)
                  },
                  {
                    label: 'Delete',
                    variant: 'destructive',
                    icon: <Trash2 className="h-4 w-4" />,
                    onClick: (tool) => setDeleteToolId(tool.id)
                  }
                ]}
              />
            )}
          </TabsContent>

          {/* Tests Tab */}
          <TabsContent value="tests" className="space-y-6">
            <StatsCarousel stats={testStatsData} />

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search tests..."
                  value={testSearch}
                  onChange={(e) => setTestSearch(e.target.value)}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 border rounded-md bg-background">
                  <Switch
                    id="show-system"
                    checked={showSystemScenarios}
                    onCheckedChange={setShowSystemScenarios}
                  />
                  <Label htmlFor="show-system" className="text-sm cursor-pointer whitespace-nowrap">
                    Show System Tests
                  </Label>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Filter className="h-4 w-4 sm:mr-1"/>
                      <span className="hidden sm:inline">{testEnvFilter === "all" ? "All Games" : titleize(testEnvFilter)}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => setTestEnvFilter("all")}>All</DropdownMenuItem>
                    {testEnvOptions.map((env) => (
                      <DropdownMenuItem key={env} onClick={() => setTestEnvFilter(env)}>
                        {titleize(env)}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button variant="brand-primary" onClick={() => navigate('/tests/new')}>
                  <Plus className="h-4 w-4" />
                  <span className="hidden sm:inline ml-2">New Test</span>
                </Button>
              </div>
            </div>

            {filteredTests.length === 0 && !testsLoading ? (
              testSearch ? (
                <EmptyState
                  icon={<Search className="h-12 w-12" />}
                  title="No tests found"
                  description={`No tests match "${testSearch}". Try a different search term.`}
                />
              ) : (
                <EmptyState
                  icon={<FlaskConical className="h-12 w-12" />}
                  title="No tests yet"
                  description="You haven't created any tests yet. Create your first test to get started."
                  action={{
                    label: "Create your first test",
                    onClick: () => navigate("/tests/new")
                  }}
                />
              )
            ) : (
              <DataTable data={filteredTests} columns={testColumns} loading={testsLoading} minWidth={440} />
            )}
          </TabsContent>
        </Tabs>

        {/* Delete Dialogs */}
        <ConfirmDialog
          open={!!deleteAgentId}
          title="Delete agent?"
          description="This action cannot be undone. All agent versions and statistics will be permanently deleted."
          onOpenChange={() => setDeleteAgentId(null)}
          onConfirm={onConfirmDeleteAgent}
        />

        <ConfirmDialog
          open={!!deleteToolId}
          title={toolConfirmTitle}
          description={toolConfirmDescription}
          confirmText={toolConfirmText}
          onOpenChange={(open) => { if (!open) setDeleteToolId(null); }}
          onConfirm={onConfirmDeleteTool}
        />

        <ConfirmDialog
          open={!!deleteTestId}
          onOpenChange={(open) => !open && setDeleteTestId(null)}
          title="Delete this test scenario?"
          description="This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          onConfirm={handleDeleteTestConfirm}
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

export default AgentManagementPage;
