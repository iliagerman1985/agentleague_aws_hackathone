import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { agentsService, GameEnvironment, loadGameEnvironmentMetadata, type GameEnvironmentMetadata, getAvailableGameEnvironments } from "@/services/agentsService";
import { type TestScenarioId } from "@/types/ids";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToasts } from "@/components/common/notifications/ToastProvider";
import { Save, ArrowLeft, Eye, FolderOpen, AlertCircle, Gamepad2 } from "lucide-react";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";

import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { SharedModal } from "@/components/common/SharedModal";
import CodeMirror from "@uiw/react-codemirror";
import { json } from "@codemirror/lang-json";
import { Switch } from "@/components/ui/switch";
import { GameStatePreview } from "@/components/games/GameStatePreview";
import { SaveGameStateDialog } from "@/components/pages/agents/dialogs/SaveGameStateDialog";
import { SavedStatesDialog } from "@/components/pages/agents/dialogs/SavedStatesDialog";
import { Badge } from "@/components/ui/badge";
import { getEnvironmentTheme } from "@/lib/environmentThemes";
const DEFAULT_STATE: Record<string, any> = {};

export default function TestEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { push } = useToasts();

  const isNew = !id;


  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [saveStateOpen, setSaveStateOpen] = useState(false);
  const [loadStatesOpen, setLoadStatesOpen] = useState(false);
  const [confirmNavigateOpen, setConfirmNavigateOpen] = useState(false);
  const [pendingNavigate, setPendingNavigate] = useState<string | null>(null);

  // Local editable fields
  const [name, setName] = useState<string>("New Test");
  const [environment, setEnvironment] = useState<GameEnvironment | null>(null);
  const [description, setDescription] = useState<string>("");
  const [stateObj, setStateObj] = useState<Record<string, any>>(DEFAULT_STATE);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSystemScenario, setIsSystemScenario] = useState<boolean>(false);

  const [jsonText, setJsonText] = useState<string>(() => JSON.stringify(stateObj ?? {}, null, 2));
  const [showJson, setShowJson] = useState<boolean>(false);



  const [descModalOpen, setDescModalOpen] = useState<boolean>(false);

  // Environment selection state
  const [availableEnvironments, setAvailableEnvironments] = useState<GameEnvironment[]>([]);
  const [envMetadata, setEnvMetadata] = useState<Record<GameEnvironment, GameEnvironmentMetadata> | null>(null);

  useEffect(() => {
    setJsonText(JSON.stringify(stateObj ?? {}, null, 2));
  }, [stateObj]);

  // Load available environments on mount
  useEffect(() => {
    const loadEnvs = async () => {
      try {
        const metadata = await loadGameEnvironmentMetadata();
        setEnvMetadata(metadata);
        setAvailableEnvironments(getAvailableGameEnvironments());
      } catch (e) {
        console.error("Failed to load environments:", e);
      }
    };
    void loadEnvs();
  }, []);

  // Navigation guard for unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  const handleNavigateAway = (path: string) => {
    if (hasUnsavedChanges) {
      setPendingNavigate(path);
      setConfirmNavigateOpen(true);
    } else {
      navigate(path);
    }
  };

  const confirmNavigateAway = () => {
    if (pendingNavigate) {
      navigate(pendingNavigate);
      setPendingNavigate(null);
    }
    setConfirmNavigateOpen(false);
  };





  useEffect(() => {
    const run = async () => {
      if (!isNew) {
        try {
          const data = await agentsService.getTestScenario(id as TestScenarioId);
          if (data) {
            setName(data.name || "");
            setEnvironment(data.environment);
            setDescription(data.description || "");
            setStateObj(data.gameState || {});
            setIsSystemScenario(data.isSystem || false);
          }
        } catch (e: any) {
          push({ title: "Failed to load", message: String(e?.message || e), tone: "error" });
        }
      }
    };
    void run();
  }, [id, isNew, push]);









  const handleSave = async () => {
    if (!name.trim()) {
      push({ title: "Name required", message: "Please enter a test name", tone: "error" });
      return;
    }
    if (!environment) {
      push({ title: "Environment required", message: "Please wait for the test to load", tone: "error" });
      return;
    }

    try {
      if (isNew) {
        // Create new test
        const created = await agentsService.createTestScenario({
          name: name.trim(),
          description: description.trim() || undefined,
          environment,
          gameState: stateObj,
          tags: [],
        });
        push({ title: "Saved", message: "Test scenario created", tone: "success" });
        setHasUnsavedChanges(false);
        navigate(`/tests/${created.id}`);
      } else {
        // Update existing test
        await agentsService.updateTestScenario(id as TestScenarioId, {
          name: name.trim(),
          description: description.trim() || undefined,
          gameState: stateObj,
        });
        push({ title: "Saved", message: "Test scenario updated", tone: "success" });
        setHasUnsavedChanges(false);
      }
    } catch (e: any) {
      push({ title: "Save failed", message: String(e?.message || e), tone: "error" });
    }
  };

  const handleSaveAs = () => {
    // Open the save dialog to let user edit name and description
    setSaveStateOpen(true);
  };

  const handleDelete = async () => {
    if (isNew || isSystemScenario) return;
    try {
      await agentsService.deleteTestScenario(id as TestScenarioId);
      push({ title: "Deleted", message: "Test scenario deleted", tone: "success" });
      navigate("/tests");
    } catch (e: any) {
      push({ title: "Delete failed", message: String(e?.message || e), tone: "error" });
    }
  };



  return (
    <div className="w-full space-y-8 px-3 py-6 md:px-4 lg:px-6 xl:px-8">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header - matching the styled format */}
        <div className="relative flex items-center justify-between mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          {/* Subtle environment art behind header */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="tests" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center gap-4 flex-1 min-w-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleNavigateAway("/tests")}
              className="bg-background/80 border shadow-sm hover:bg-accent hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Back to Tests</span>
            </Button>
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal">
                  {isNew ? "Create Test" : "Edit Test"}
                </h1>
                {isSystemScenario && (
                  <Badge variant="secondary" className="shrink-0">
                    System Test
                  </Badge>
                )}
              </div>
              <p className="hidden sm:block text-muted-foreground text-lg">Manage and run a test scenario.</p>
            </div>
          </div>
        </div>

      {/* Name field */}
      <div className="space-y-2">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Test name"
          className="text-2xl font-semibold h-12"
          disabled={isSystemScenario}
          readOnly={isSystemScenario}
        />
        {isSystemScenario && (
          <p className="text-sm text-muted-foreground">
            This is a system test scenario. You can view and use "Save As" to create your own copy.
          </p>
        )}
      </div>

      <ConfirmDialog
        open={confirmDeleteOpen}
        onOpenChange={setConfirmDeleteOpen}
        title="Delete this test scenario?"
        description="This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleDelete}
      />

      {/* Editor */}
      <div className="space-y-4">
        {/* Unsaved changes indicator */}
        {hasUnsavedChanges && (
          <div className="rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-900/20 p-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <span className="text-sm text-amber-700 dark:text-amber-300">You have unsaved changes</span>
          </div>
        )}

        {/* Environment Selection for New Tests */}
        {isNew && !environment && (
          <div className="rounded-lg border p-6 bg-card space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Gamepad2 className="h-5 w-5 text-brand-teal" />
              <h3 className="text-lg font-semibold text-foreground">Select Game Environment</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Choose the game environment for this test scenario. This determines what type of game state you'll be testing.
            </p>

            <div className="space-y-3">
              {availableEnvironments.map((env) => {
                const metadata = envMetadata?.[env];
                if (!metadata) return null;
                const theme = getEnvironmentTheme(env);
                const EnvIcon = theme.icon;
                return (
                  <div
                    key={env}
                    className={`relative p-4 border rounded-lg cursor-pointer transition-colors overflow-hidden ${
                      environment === env
                        ? 'border-brand-teal bg-brand-teal/5'
                        : 'border-border hover:border-brand-teal/50'
                    }`}
                    onClick={() => {
                      setEnvironment(env);
                      setHasUnsavedChanges(true);
                    }}
                  >
                    {/* Environment-themed background gradient */}
                    <div
                      className="absolute inset-0 pointer-events-none"
                      style={{
                        background: `linear-gradient(to bottom right, ${theme.colors.primary}15, ${theme.colors.accent}10, transparent)`,
                      }}
                    />

                    <div className="relative z-10">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-foreground flex items-center gap-2">
                          <span style={{ color: theme.colors.primary }}>
                            <EnvIcon className="h-4 w-4" />
                          </span>
                          {metadata.displayName}
                        </h4>
                        {environment === env && (
                          <Badge className="bg-brand-teal text-white">Selected</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{metadata.description}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline" className="text-xs">
                          {metadata.minPlayers}-{metadata.maxPlayers} players
                        </Badge>
                        {metadata.hasBetting && (
                          <Badge variant="outline" className="text-xs">Betting</Badge>
                        )}
                        {metadata.isTurnBased && (
                          <Badge variant="outline" className="text-xs">Turn-based</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Instructions - only show after environment is selected */}
        {environment && (
          <div className="rounded-lg border p-3 bg-card">
            <h3 className="font-semibold">How to use Tests</h3>
            <ul className="text-sm text-muted-foreground list-disc pl-5">
              <li>Load an existing test state or start with a fresh state.</li>
              <li>Edit the JSON directly or toggle to view the game state visually.</li>
              <li>Save your changes or save as a new test.</li>
            </ul>
          </div>
        )}

        {/* Controls - only show after environment is selected */}
        {environment && (
          <div className="flex flex-wrap items-center gap-3 w-full">
            <div className="flex items-center gap-2 flex-wrap">
              <Button size="sm" variant="outline" onClick={() => setLoadStatesOpen(true)}>
                <FolderOpen className="h-4 w-4 mr-1" /> Load State
              </Button>
              {!isSystemScenario && (
                <Button size="sm" variant="brand-primary" onClick={handleSave} className="hover:bg-[var(--brand-primary-red)]">
                  <Save className="h-4 w-4 mr-1" /> {isNew ? 'Save' : 'Save'}
                </Button>
              )}
              {(!isNew || isSystemScenario) && (
                <Button size="sm" variant={isSystemScenario ? "brand-primary" : "outline"} onClick={handleSaveAs}>
                  <Save className="h-4 w-4 mr-1" /> Save As
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => setDescModalOpen(true)}>
                <Eye className="h-4 w-4 mr-1" /> Description
              </Button>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-muted-foreground">JSON</span>
              <Switch checked={showJson} onCheckedChange={setShowJson} />
            </div>
          </div>
        )}

        {/* Interactive Editor or JSON/Visual preview - only show after environment is selected */}
        {environment && (
          <div className="rounded-lg border bg-card p-2 relative overflow-hidden">
            <EnvironmentBackground environment={environment} opacity={0.12} className="absolute inset-0 pointer-events-none" />
            <div className="relative z-10">
            {showJson ? (
              <CodeMirror
                value={jsonText}
                height="60vh"
                extensions={[json()]}
                theme={"dark"}
                onChange={(v) => {
                  setJsonText(v);
                  try {
                    const parsed = JSON.parse(v);
                    setStateObj(parsed);
                    setHasUnsavedChanges(true);
                  } catch {
                    /* ignore parse errors, preview handles fallback */
                  }
                }}
              />
            ) : (
              <GameStatePreview
                environment={environment}
                jsonText={jsonText}
                onJsonChange={(newJson) => {
                  setJsonText(newJson);
                  setHasUnsavedChanges(true);
                  try {
                    setStateObj(JSON.parse(newJson));
                  } catch {
                    /* ignore parse errors */
                  }
                }}
                editable={true}
              />
            )}
            </div>
          </div>
        )}



      </div>



      {/* State save/load dialogs */}
      <SaveGameStateDialog
        open={saveStateOpen}
        onOpenChange={setSaveStateOpen}
        environment={environment ?? undefined}
        gameState={stateObj}
        initialName={name ? `${name} (Copy)` : ''}
        initialDescription={description}
        onSaved={(savedState) => {
          setHasUnsavedChanges(false);
          // Navigate to the newly created test
          if (savedState?.id) {
            navigate(`/tests/${savedState.id}`);
          }
        }}
      />
      <SavedStatesDialog
        open={loadStatesOpen}
        onOpenChange={setLoadStatesOpen}
        environment={environment ?? undefined}
        onLoadState={(st, desc) => {
          setStateObj(st);
          if (typeof desc === "string") setDescription(desc);
          setJsonText(JSON.stringify(st ?? {}, null, 2));
          setHasUnsavedChanges(false);
        }}
      />

      {/* Description modal */}
      <SharedModal
        open={descModalOpen}
        onOpenChange={setDescModalOpen}
        title="Scenario Description"
        description="Details"
        size="lg"
      >
        <div className="space-y-3">
          <div className="text-sm whitespace-pre-wrap">
            {description || "No description provided."}
          </div>
        </div>
      </SharedModal>

      {/* Navigation guard dialog */}
      <ConfirmDialog
        open={confirmNavigateOpen}
        onOpenChange={setConfirmNavigateOpen}
        title="Unsaved Changes"
        description="You have unsaved changes. Are you sure you want to leave? Your changes will be lost."
        confirmText="Leave"
        cancelText="Stay"
        onConfirm={confirmNavigateAway}
      />

      </div>
    </div>
  );
}

