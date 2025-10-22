import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toolsService, type Tool, type GameEnvironment } from "@/services/toolsService";
import { getAvailableGameEnvironments } from "@/services/agentsService";
import { type ToolId } from "@/types/ids";
import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ActionTable } from "@/components/common/tables/ActionTable";
import { EmptyState } from "@/components/common/utility/EmptyState";
import { usePersistentView } from "@/components/common/utility/ViewSelector";
import { StatsCarousel } from "@/components/common/utility/StatsCarousel";
import type { StatItem } from "@/components/common/utility/StatsCarousel";

import { SearchAndViewSelector } from "@/components/common/utility/SearchAndViewSelector";
import { Plus, Search, Pencil, Trash2, Code, Clock, Calendar, Wrench } from "lucide-react";
import { ItemCard } from "@/components/common/cards/ItemCard";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
export const ToolListPage: React.FC = () => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<ToolId | null>(null);
  const [usage, setUsage] = useState<{ agents: { id: string; name: string }[]; agentsCount: number } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [environmentFilter, setEnvironmentFilter] = useState<GameEnvironment | "all">("all");
  const [viewType, setViewType] = usePersistentView('tools', 'grid');
  const navigate = useNavigate();

  useEffect(() => {
    toolsService.list().then(setTools).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!deleteId) { setUsage(null); return; }
    toolsService.usage(deleteId)
      .then(setUsage)
      .catch(() => setUsage({ agents: [], agentsCount: 0 }));
  }, [deleteId]);


  const onConfirmDelete = async () => {
    if (!deleteId) return;
    if (usage && usage.agentsCount > 0) {
      await toolsService.deleteWithDetach(deleteId);
    } else {
      await toolsService.delete(deleteId);
    }
    setTools(await toolsService.list());
    setDeleteId(null);
  };

  // Filter tools based on search query and environment
  const filteredTools = tools.filter(tool => {
    const matchesSearch = (tool.displayName || "").toLowerCase().includes(searchQuery.toLowerCase());

    // Get available environments to filter by
    const availableEnvs = getAvailableGameEnvironments();
    const isToolEnvAvailable = availableEnvs.includes(tool.environment as any);

    // Show tool only if its environment is available or if a specific filter is applied
    if (environmentFilter === "all") {
      return matchesSearch && isToolEnvAvailable;
    }

    return matchesSearch && tool.environment === environmentFilter;
  });

  // Calculate stats from tools data - only count tools from available environments
  const availableEnvs = getAvailableGameEnvironments();
  const toolsInActiveEnvs = tools.filter(t => availableEnvs.includes(t.environment as any));

  const totalTools = toolsInActiveEnvs.length;
  const recentlyUpdated = toolsInActiveEnvs.filter((tool) => {
    const updatedDate = new Date(tool.updatedAt);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return updatedDate > weekAgo;
  }).length;
  const averageCodeLength = toolsInActiveEnvs.length > 0
    ? Math.round(toolsInActiveEnvs.reduce((sum, tool) => sum + tool.code.length, 0) / toolsInActiveEnvs.length)
    : 0;

  const getTruncated = (value: string, length: number) => {
    if (value.length <= length) {
      return value;
    }
    return `${value.slice(0, Math.max(0, length - 1))}…`;
  };

  // Remove the markdown heading '### Human-Readable Description' if it appears at the start
  const cleanDescription = (value?: string): string => {
    if (!value) return "";
    return value.replace(/^\s*#+\s*Human-Readable Description\s*/i, "").trim();
  };


  // Stats data for the carousel
  const statsData: StatItem[] = [
    {
      icon: <Wrench className="h-5 w-5 sm:h-6 sm:w-6 text-sky-500" />,
      label: "Total Tools",
      value: totalTools.toString(),
      description: "Custom utilities created",
      variant: "sky",
    },
    {
      icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-amber-500" />,
      label: "Recently Updated",
      value: recentlyUpdated.toString(),
      description: "Touched this week",
      variant: "amber",
    },
    {
      icon: <Code className="h-5 w-5 sm:h-6 sm:w-6 text-cyan-500" />,
      label: "Avg. Size",
      value: `${averageCodeLength}`,
      description: "Characters per tool",
      variant: "cyan",
    }
  ];

  const confirmText = usage && usage.agentsCount > 0 ? "Remove from agents and delete" : "Delete";
  const confirmTitle = usage && usage.agentsCount > 0 ? "Tool is in use" : "Delete tool?";
  const confirmDescription = usage && usage.agentsCount > 0
    ? `This tool is used by ${usage.agentsCount} agent(s): ${usage.agents.map(a => a.name).join(', ')}. Continuing will remove it from these agents and delete the tool.`
    : "This action cannot be undone.";

  return (
    <div className="w-full space-y-8 p-6 lg:p-8" data-testid="tool-list-page">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header - matching the home example */}
        <div className="relative mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6" data-testid="tool-list-header">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="tools" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-foreground mb-0 sm:mb-2" data-testid="tool-list-title">My Tools</h1>
              <p className="hidden sm:block text-muted-foreground text-lg" data-testid="tool-list-subtitle">
                Create and manage your custom tools
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button asChild variant="brand-primary" data-testid="create-tool-button">
                <Link to="/tools/new">
                  <Plus className="h-4 w-4" />
                  <span className="hidden sm:inline ml-2">Create Tool</span>
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {/* Stats Carousel */}
        <StatsCarousel stats={statsData} />

        {/* Search and View Selector section */}
        <SearchAndViewSelector
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Search tools..."
          viewType={viewType}
          onViewChange={setViewType}
          rightSlot={
            <Select value={environmentFilter} onValueChange={(value) => setEnvironmentFilter(value as GameEnvironment | "all")}>
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
          }
        />

        {/* Tools content */}
        {filteredTools.length === 0 && !loading ? (
          searchQuery ? (
            <EmptyState
              icon={<Search className="h-12 w-12" />}
              title="No tools found"
              description={`No tools match "${searchQuery}". Try a different search term.`}
              data-testid="tool-list-empty-search"
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
              data-testid="tool-list-empty-state"
            />
          )
        ) : viewType === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6 justify-center" data-testid="tool-list-grid-view">
            {filteredTools.map((tool) => (
              <ItemCard
                size="lg"
                key={tool.id}
                  icon={<Code className="h-6 w-6 text-orange-500" />}
                  title={tool.displayName}
                  description={cleanDescription(tool.description) || undefined}
                  showEnvironmentArt={true}
                  environment="generic"
                  belowTitle={
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          {tool.environment === 'texas_holdem' ? 'Texas Hold\'em' : 'Chess'}
                        </Badge>
                        <div className="flex items-center gap-1 whitespace-nowrap text-muted-foreground">
                          <Calendar className="h-4 w-4" />
                          <span>{new Date(tool.updatedAt).toLocaleString(undefined, { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </div>
                    </div>
                  }
                  features={null}
                  bottomLeft={
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Code className="h-4 w-4" />
                        <span>{tool.code.length} chars</span>
                      </div>
                      <Badge className={
                        tool.validationStatus === 'valid'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : tool.validationStatus === 'pending'
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                            : 'bg-red-500/15 text-red-400 border border-red-500/30'
                      }>
                        {tool.validationStatus.toUpperCase()}
                      </Badge>
                    </div>
                  }
                  actions={
                    <>
                      <Button variant="outline" size="sm" onClick={() => navigate(`/tools/${tool.id}`)} data-testid={`edit-tool-button-${tool.id}`}>
                        <Pencil className="h-4 w-4 mr-2" />
                        Edit
                      </Button>
                      <Button variant="destructive" size="sm" onClick={() => setDeleteId(tool.id)} data-testid={`delete-tool-button-${tool.id}`}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </Button>
                    </>
                  }
                />
            ))}
          </div>
        ) : (
      <ActionTable
              data={filteredTools}
              loading={loading}
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
                        <p
                          className="text-sm font-medium text-foreground sm:text-base sm:leading-5"
                          title={tool.displayName}
                        >
                          <span className="sm:hidden">{getTruncated(tool.displayName, 22)}</span>
                          <span className="hidden sm:inline">{tool.displayName}</span>
                        </p>
                        {tool.description && (
                          <p
                            className="text-[11px] text-muted-foreground leading-4 sm:text-xs line-clamp-1 sm:line-clamp-2"
                            title={cleanDescription(tool.description)}
                          >
                            {cleanDescription(tool.description)}
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
                  onClick: (tool) => setDeleteId(tool.id)
                }
              ]}
              data-testid="tool-list-table-view"
            />
        )}

        <ConfirmDialog
          open={!!deleteId}
          title={confirmTitle}
          description={confirmDescription}
          confirmText={confirmText}
          onOpenChange={(open) => { if (!open) setDeleteId(null); }}
          onConfirm={onConfirmDelete}
          data-testid="tool-delete-confirm-dialog"
        />
      </div>
    </div>
  );
};

export default ToolListPage;

