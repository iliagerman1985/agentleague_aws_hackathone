import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { agentsService, type TestScenarioResponse, GameEnvironment, getAvailableGameEnvironments } from "@/services/agentsService";
import { SearchAndViewSelector } from "@/components/common/utility/SearchAndViewSelector";
import { usePersistentView } from "@/components/common/utility/ViewSelector";
import { ItemCard } from "@/components/common/cards/ItemCard";
import { DataTable } from "@/components/common/tables/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Plus, Filter, Copy, Pencil, Trash2, Eye } from "lucide-react";
import { useToasts } from "@/components/common/notifications/ToastProvider";
import { type TestScenarioId } from "@/types/ids";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { StatsCarousel } from "@/components/common/utility/StatsCarousel";
import type { StatItem } from "@/components/common/utility/StatsCarousel";

import { TestTube, Clock, Calendar, Beaker } from "lucide-react";
import { getEnvironmentTheme } from "@/lib/environmentThemes";

export const TestListPage: React.FC = () => {
  const navigate = useNavigate();
  const { push } = useToasts();

  const [scenarios, setScenarios] = useState<TestScenarioResponse[]>([]);
  const [search, setSearch] = useState("");
  const [view, setView] = usePersistentView("tests", "grid");
  const [envFilter, setEnvFilter] = useState<"all" | GameEnvironment>("all");
  const [showSystemScenarios, setShowSystemScenarios] = useState<boolean>(() => {
    const saved = localStorage.getItem("tests-show-system-scenarios");
    return saved !== null ? saved === "true" : true; // Default to true
  });

  const [envOptions, setEnvOptions] = useState<GameEnvironment[]>([]);
  const [deleteId, setDeleteId] = useState<TestScenarioId | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const agents = await agentsService.list();
        const availableEnvs = getAvailableGameEnvironments();
        const envs = Array.from(new Set(agents.map(a => a.gameEnvironment)))
          .filter(env => availableEnvs.includes(env)) as GameEnvironment[];
        setEnvOptions(envs);
      } catch {
        setEnvOptions([]);
      }
    };
    void run();
  }, []);


  const titleize = (s: string) => s.split("_").map(w => w ? (w[0].toUpperCase() + w.slice(1)) : w).join(" ");
  const [isLoading, setIsLoading] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await agentsService.getTestScenarios({ includeSystem: showSystemScenarios });
      setScenarios(list || []);
    } catch (e: any) {
      push({ title: "Failed to load tests", message: String(e?.message || e), tone: "error" });
    } finally {
      setIsLoading(false);
    }
  }, [push, showSystemScenarios]);

  useEffect(() => { void load(); }, [load]);

  // Save preference to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("tests-show-system-scenarios", String(showSystemScenarios));
  }, [showSystemScenarios]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return scenarios.filter((s) => {
      // Get available environments to filter by
      const availableEnvs = getAvailableGameEnvironments();
      const isTestEnvAvailable = availableEnvs.includes(s.environment as any);

      // Show test only if its environment is available or if a specific filter is applied
      const matchesEnv = envFilter === "all"
        ? isTestEnvAvailable
        : s.environment === envFilter;
      const matchesSearch = !q || s.name.toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q);
      return matchesEnv && matchesSearch;
    });
  }, [scenarios, envFilter, search]);

  // Calculate stats from test scenarios - only count tests from available environments
  const availableEnvs = getAvailableGameEnvironments();
  const testsInActiveEnvs = scenarios.filter(s => availableEnvs.includes(s.environment as any));

  const totalTests = testsInActiveEnvs.length;
  const userTests = testsInActiveEnvs.filter(s => !s.isSystem).length;
  const systemTests = testsInActiveEnvs.filter(s => s.isSystem).length;
  const recentlyUpdated = testsInActiveEnvs.filter(s => {
    const updatedDate = new Date(s.updatedAt);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return updatedDate > weekAgo;
  }).length;

  // Stats data for the carousel
  const statsData: StatItem[] = [
    {
      icon: <TestTube className="h-5 w-5 sm:h-6 sm:w-6 text-cyan-500" />,
      label: "Total Tests",
      value: totalTests.toString(),
      description: "Test scenarios created",
      variant: "cyan",
    },
    {
      icon: <Beaker className="h-5 w-5 sm:h-6 sm:w-6 text-indigo-500" />,
      label: "User Tests",
      value: userTests.toString(),
      description: "Custom scenarios",
      variant: "indigo",
    },
    {
      icon: <Clock className="h-5 w-5 sm:h-6 sm:w-6 text-amber-500" />,
      label: "System Tests",
      value: systemTests.toString(),
      description: "Predefined scenarios",
      variant: "amber",
    },
    {
      icon: <Calendar className="h-5 w-5 sm:h-6 sm:w-6 text-emerald-500" />,
      label: "This Week",
      value: recentlyUpdated.toString(),
      description: "New updates",
      variant: "emerald",
    }
  ];

  const duplicate = async (row: TestScenarioResponse) => {
    try {
      await agentsService.createTestScenario({
        name: `Copy of ${row.name}`,
        description: row.description || undefined,
        environment: row.environment,
        gameState: row.gameState || {},
        tags: [],
      });
      push({ title: "Duplicated", message: `Created copy of ${row.name}`, tone: "success" });
      void load();
    } catch (e: any) {
      push({ title: "Duplicate failed", message: String(e?.message || e), tone: "error" });
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteId) return;
    try {
      await agentsService.deleteTestScenario(deleteId);
      push({ title: "Deleted", message: "Test scenario deleted", tone: "success" });
      setDeleteId(null);
      void load();
    } catch (e: any) {
      push({ title: "Delete failed", message: String(e?.message || e), tone: "error" });
      setDeleteId(null);
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

  const columns = [
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
            onClick={() => duplicate(item)}
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
            onClick={() => setDeleteId(item.id)}
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
    <div className="w-full space-y-8 p-6 lg:p-8">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
      {/* Header */}
      <div className="relative mb-6 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
        <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
          <EnvironmentBackground environment="tests" opacity={0.20} />
        </div>
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-1 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal">Tests</h1>
            <p className="hidden sm:block text-muted-foreground">Manage and edit your test scenarios.</p>
          </div>
          <Button variant="brand-primary" onClick={() => navigate("/tests/new")}>
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline ml-2">New Test</span>
          </Button>
        </div>
      </div>

      {/* Stats Carousel */}
      <StatsCarousel stats={statsData} />

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <SearchAndViewSelector
          searchQuery={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search tests..."
          viewType={view}
          onViewChange={setView}
          rightSlot={(
            <div className="flex items-center gap-2">
              {/* System Scenarios Toggle */}
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

              {/* Environment Filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter className="h-4 w-4 sm:mr-1"/>
                    <span className="hidden sm:inline">{envFilter === "all" ? "All Games" : titleize(envFilter)}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setEnvFilter("all")}>All</DropdownMenuItem>
                  {envOptions.map((env) => (
                    <DropdownMenuItem key={env} onClick={() => setEnvFilter(env)}>
                      {titleize(env)}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}
        />
      </div>

      {/* Content */}
      {view === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((s) => {
            const theme = getEnvironmentTheme(s.environment);
            return (
              <ItemCard
                key={s.id}
                size="lg"
                icon={React.createElement(theme.icon, { className: `h-5 w-5 ${theme.iconColor}` })}
                title={s.name}
                description={s.description || ""}
                environment={s.environment}
                showEnvironmentArt={true}
                onClick={s.isSystem ? undefined : () => navigate(`/tests/${s.id}`)}
                actions={
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); navigate(`/tests/${s.id}`); }}
                    title={s.isSystem ? "View system test" : "Edit test"}
                  >
                    {s.isSystem ? <Eye className="h-4 w-4 mr-1"/> : <Pencil className="h-4 w-4 mr-1"/>}
                    {s.isSystem ? "View" : "Edit"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); void duplicate(s); }}>
                    <Copy className="h-4 w-4 mr-1"/> Duplicate
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={(e) => { e.stopPropagation(); setDeleteId(s.id); }}
                    disabled={s.isSystem}
                    title={s.isSystem ? "System tests cannot be deleted" : "Delete test"}
                  >
                    <Trash2 className="h-4 w-4 mr-1"/> Delete
                  </Button>
                </div>
              }
              bottomLeft={<div className="text-xs text-muted-foreground">{titleize(s.environment)}</div>}
            />
            );
          })}
        </div>
      ) : (
        <DataTable data={filtered} columns={columns} loading={isLoading} minWidth={440} />
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteId}
        onOpenChange={(open) => !open && setDeleteId(null)}
        title="Delete this test scenario?"
        description="This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleDeleteConfirm}
      />
      </div>
    </div>
  );
};

