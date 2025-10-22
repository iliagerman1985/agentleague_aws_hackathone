import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Textarea } from "@/components/ui/textarea";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { agentsService, type GameEnvironment, type VariableInfo } from "@/services/agentsService";
import { Bot, FileText, StopCircle, Lightbulb, Code, AlertCircle, Sparkles, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AgentInstructionsTabProps {
  systemPrompt: string;
  conversationInstructions: string;
  exitCriteria: string;
  gameEnvironment: GameEnvironment;
  onSystemPromptChange: (value: string) => void;
  onConversationInstructionsChange: (value: string) => void;
  onExitCriteriaChange: (value: string) => void;
  // Optional errors provided by parent (e.g., on Save validation)
  externalErrors?: string[];
  hasSystemPromptError?: boolean;
}

export const AgentInstructionsTab: React.FC<AgentInstructionsTabProps> = ({
  systemPrompt,
  conversationInstructions,
  exitCriteria,
  gameEnvironment,
  onSystemPromptChange,
  onConversationInstructionsChange,
  onExitCriteriaChange,
  externalErrors,
  hasSystemPromptError = false,
}) => {
  // Mode handling
  const INJECTION_PREFIX = "This is the current state ${{state}}.\n\n";
  const hasInjection = (val: string) => val?.startsWith(INJECTION_PREFIX);
  const stripInjection = (val: string) => hasInjection(val) ? val.slice(INJECTION_PREFIX.length) : val;

  const initializedMode = useRef(false);
  const [mode, setMode] = useState<"default" | "advanced">("default");

  const [availableVariables, setAvailableVariables] = useState<VariableInfo[]>([]);
  const [filteredVariables, setFilteredVariables] = useState<VariableInfo[]>([]);
  const [varSearch, setVarSearch] = useState("");
  const [loadingVariables, setLoadingVariables] = useState(true);
  const [validationErrors] = useState<string[]>([]);

  // Autocomplete state
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<VariableInfo[]>([]);
  const [selectedSuggestionIdx, setSelectedSuggestionIdx] = useState(0);
  const [anchor, setAnchor] = useState<{left: number; top: number; width: number; maxHeight: number} | null>(null);
  const [activeField, setActiveField] = useState<"system" | "conversation" | "exit" | null>(null);

  useEffect(() => {
    loadEnvironmentSchema();
  }, [gameEnvironment]);

  // Initialize mode: always default on mount and ensure injection prefix exists
  useEffect(() => {
    if (initializedMode.current) return;
    setMode("default");
    if (!hasInjection(systemPrompt)) {
      onSystemPromptChange(INJECTION_PREFIX + (systemPrompt || ""));
    }
    initializedMode.current = true;
    // Run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When switching modes, add or remove injection automatically (not visible in default mode UI)
  useEffect(() => {
    if (!initializedMode.current) return;
    if (mode === "default") {
      if (!hasInjection(systemPrompt)) {
        onSystemPromptChange(INJECTION_PREFIX + systemPrompt);
      }
    } else {
      if (hasInjection(systemPrompt)) {
        onSystemPromptChange(stripInjection(systemPrompt));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Reposition suggestions on scroll/resize so they remain visible and not clipped
  useEffect(() => {
    const reposition = () => {
      if (!showSuggestions || !activeField) return;
      const ref = activeField === "system" ? systemPromptRef : activeField === "conversation" ? conversationRef : exitRef;
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const available = Math.max(120, Math.min(240, window.innerHeight - rect.bottom - 8));
      setAnchor({ left: rect.left, top: rect.bottom + 4, width: rect.width, maxHeight: available });
    };
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    return () => {
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
  }, [showSuggestions, activeField]);

  // Do not validate on each change; validation will run on Save from the parent

  const loadEnvironmentSchema = async () => {
    try {
      setLoadingVariables(true);
      const schema = await agentsService.getEnvironmentSchema(gameEnvironment);
      setAvailableVariables(schema.variables);
      setFilteredVariables(schema.variables);
      setVarSearch("");
    } catch (error) {
      console.error("Failed to load environment schema:", error);
    } finally {
      setLoadingVariables(false);
    }
  };

  // Validation runs on Save from the parent page; keep state here for optional display

  const systemPromptRef = React.useRef<HTMLTextAreaElement | null>(null);
  const conversationRef = React.useRef<HTMLTextAreaElement | null>(null);
  const exitRef = React.useRef<HTMLTextAreaElement | null>(null);

  const insertVariable = (variable: VariableInfo) => {
    const variableText = `\${{${variable.path}}}`;
    const textarea = systemPromptRef.current;
    if (textarea) {
      const start = textarea.selectionStart ?? systemPrompt.length;
      const end = textarea.selectionEnd ?? systemPrompt.length;
      const newValue = systemPrompt.substring(0, start) + variableText + systemPrompt.substring(end);
      onSystemPromptChange(newValue);
      // Set cursor position after the inserted variable
      setTimeout(() => {
        textarea.focus();
        const pos = start + variableText.length;
        textarea.setSelectionRange(pos, pos);
      }, 0);
    } else {
      onSystemPromptChange(systemPrompt + variableText);
    }
  };

  // Helpers for autocomplete
  function getVarContext(value: string, cursor: number): { inside: boolean; innerStart: number; innerEnd: number; content: string } {
    // Find the last opening token before the cursor
    const open = value.lastIndexOf("${{", cursor);
    if (open === -1) return { inside: false, innerStart: -1, innerEnd: -1, content: "" };
    const innerStart = open + 3;
    // Find closing braces, if present
    const close = value.indexOf("}}", innerStart);
    const innerEnd = close === -1 ? cursor : close;
    // Outside if cursor is before opening or after the closing braces
    if (cursor < innerStart) return { inside: false, innerStart: -1, innerEnd: -1, content: "" };
    if (close !== -1 && cursor > close + 1) return { inside: false, innerStart: -1, innerEnd: -1, content: "" };
    return { inside: true, innerStart, innerEnd, content: value.substring(innerStart, innerEnd) };
  }

  function filterSuggestions(prefix: string): VariableInfo[] {
    const p = prefix.trim();
    if (!p) return availableVariables.slice(0, 50);
    const starts = availableVariables.filter(v => v.path.startsWith(p));
    const contains = availableVariables.filter(v => !v.path.startsWith(p) && v.path.includes(p));
    const ranked = [...starts, ...contains];
    return ranked.slice(0, 50);
  }

  const updateAnchorFromRef = (ref: React.RefObject<HTMLTextAreaElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const available = Math.max(120, Math.min(240, window.innerHeight - rect.bottom - 8));
    setAnchor({ left: rect.left, top: rect.bottom + 4, width: rect.width, maxHeight: available });
  };

  const handleFieldChange = (field: "system" | "conversation" | "exit", val: string) => {
    if (field === "system") {
      if (mode === "default") {
        // Keep injection in stored value, but not visible in UI
        onSystemPromptChange(INJECTION_PREFIX + stripInjection(val));
      } else {
        onSystemPromptChange(val);
      }
    }
    else if (field === "conversation") onConversationInstructionsChange(val);
    else onExitCriteriaChange(val);

    const ref = field === "system" ? systemPromptRef : field === "conversation" ? conversationRef : exitRef;
    const textarea = ref.current;
    if (!textarea) return;
    const cursor = textarea.selectionStart ?? val.length;
    if (mode !== "advanced") {
      // No autocomplete in default mode
      setShowSuggestions(false);
      setSuggestions([]);
      return;
    }
    const ctx = getVarContext(val, cursor);
    setActiveField(field);
    if (ctx.inside) {
      const list = filterSuggestions(ctx.content);
      setSuggestions(list);
      setSelectedSuggestionIdx(0);
      setShowSuggestions(list.length > 0);
      updateAnchorFromRef(ref);
    } else {
      setShowSuggestions(false);
      setSuggestions([]);
    }
  };

  const handleSystemPromptChange = (val: string) => handleFieldChange("system", val);

  const applySuggestion = (suggestion: VariableInfo) => {
    const ref = activeField === "system" ? systemPromptRef : activeField === "conversation" ? conversationRef : exitRef;
    const textarea = ref.current;
    if (!textarea || !activeField) return;
    const full = activeField === "system" ? systemPrompt : activeField === "conversation" ? conversationInstructions : exitCriteria;
    const cursor = textarea.selectionStart ?? full.length;
    const ctx = getVarContext(full, cursor);
    if (!ctx.inside) return;
    const newValue = full.substring(0, ctx.innerStart) + suggestion.path + full.substring(ctx.innerEnd);
    if (activeField === "system") onSystemPromptChange(newValue);
    else if (activeField === "conversation") onConversationInstructionsChange(newValue);
    else onExitCriteriaChange(newValue);
    setShowSuggestions(false);
    setTimeout(() => {
      const pos = ctx.innerStart + suggestion.path.length;
      textarea.focus();
      textarea.setSelectionRange(pos, pos);
    }, 0);
  };

  const onSystemPromptKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (mode !== "advanced") return; // disable autocomplete key handling in default mode
    if (!showSuggestions || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedSuggestionIdx((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedSuggestionIdx((i) => (i - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      applySuggestion(suggestions[selectedSuggestionIdx]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setShowSuggestions(false);
    }
  };


  return (
    <div className="flex flex-col h-full min-h-0 space-y-6">
      {/* Header */}
      <div className="shrink-0">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Agent Instructions</h3>
            <p className="text-muted-foreground">
              Configure how your agent thinks, behaves, and makes decisions during gameplay.
            </p>
          </div>
          {/* Desktop: mode toggle stays on the right */}
          <div className="hidden md:flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Mode</span>
            <div className="bg-muted/60 p-1 rounded-lg flex items-center">
              <Button
                size="sm"
                variant={mode === "default" ? "default" : "ghost"}
                className="rounded-md"
                onClick={() => setMode("default")}
                data-testid="instructions-mode-default"
                title="Default: state injected, no variables UI or autocomplete"
              >
                <Sparkles className="h-5 w-5 sm:h-4 sm:w-4 mr-1" /> Default
              </Button>
              <Button
                size="sm"
                variant={mode === "advanced" ? "default" : "ghost"}
                className="rounded-md ml-1"
                onClick={() => setMode("advanced")}
                data-testid="instructions-mode-advanced"
                title="Advanced: raw prompt, variables UI and autocomplete enabled"
              >
                <Settings2 className="h-5 w-5 sm:h-4 sm:w-4 mr-1" /> Advanced
              </Button>
            </div>
          </div>
        </div>
        {/* Mobile: mode toggle gets its own full row under the header */}
        <div className="md:hidden mt-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-muted-foreground">Mode</span>
            <div className="bg-muted/60 p-1 rounded-lg flex items-center">
              <Button
                size="sm"
                variant={mode === "default" ? "default" : "ghost"}
                className="rounded-md"
                onClick={() => setMode("default")}
                data-testid="instructions-mode-default-mobile"
              >
                <Sparkles className="h-5 w-5 mr-1" /> Default
              </Button>
              <Button
                size="sm"
                variant={mode === "advanced" ? "default" : "ghost"}
                className="rounded-md ml-1"
                onClick={() => setMode("advanced")}
                data-testid="instructions-mode-advanced-mobile"
              >
                <Settings2 className="h-5 w-5 mr-1" /> Advanced
              </Button>
            </div>
          </div>
        </div>

        {mode === "advanced" && (
          <div className="mt-3 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            Advanced mode gives you full control of the raw prompt. The current game state is not injected automatically,
            and you can use Template Variables (with autocomplete) to reference state explicitly.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Main Instructions */}
        <div className="lg:col-span-2 space-y-6 min-h-0 pr-1">
          {/* System Prompt */}
          <Card className="relative overflow-hidden">
            <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                System Prompt
              </CardTitle>
              <CardDescription>
                The core instructions that define your agent's personality, strategy, and decision-making approach.
                {mode === "advanced" ? (
                  <>
                    {" "}Use template variables like $&#123;&#123;player.chips&#125;&#125; to access game state.
                  </>
                ) : (
                  <>
                    {" "}In Default mode, the current game state is automatically provided to the model.
                  </>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="system-prompt" className={hasSystemPromptError ? "text-destructive" : undefined}>
                    System Prompt *
                  </Label>
                  {hasSystemPromptError ? (
                    <span className="text-xs text-destructive">System prompt is required</span>
                  ) : !systemPrompt.trim() && (
                    <span className="text-xs text-muted-foreground">Add core instructions for your agent.</span>
                  )}
                </div>
                <div className="relative">
                  <Textarea
                    id="system-prompt"
                    value={mode === "default" ? stripInjection(systemPrompt) : systemPrompt}
                    onChange={(e) => handleSystemPromptChange(e.target.value)}
                    onKeyDown={onSystemPromptKeyDown}
                    onBlur={() => setShowSuggestions(false)}
                    placeholder="You are a skilled poker agent. Your goal is to maximize winnings while playing strategically..."
                    className={`min-h-[200px] font-mono text-sm ${
                      (externalErrors && externalErrors.length > 0) || hasSystemPromptError
                        ? 'border-destructive focus-visible:ring-destructive'
                        : (!systemPrompt.trim() ? 'border-dashed border-primary/60' : '')
                    }`}
                    aria-invalid={!!(externalErrors && externalErrors.length > 0)}
                    required
                    ref={systemPromptRef}
                  />
                  {mode === "advanced" && showSuggestions && suggestions.length > 0 && anchor && typeof document !== 'undefined' && (
                    createPortal(
                      <div
                        className="fixed z-[9999] overflow-auto rounded-md border border-border bg-card text-foreground shadow-xl"
                        style={{ left: anchor.left, top: anchor.top, width: anchor.width, maxHeight: anchor.maxHeight }}
                      >
                        {suggestions.map((s, idx) => (
                          <div
                            key={s.path}
                            className={`px-3 py-2 text-sm cursor-pointer ${idx === selectedSuggestionIdx ? 'bg-brand-teal/10' : ''}`}
                            onMouseDown={(e) => { e.preventDefault(); applySuggestion(s); }}
                          >
                            <div className="flex items-center justify-between gap-2 min-w-0">
                              <span className="font-mono text-foreground truncate flex-1 min-w-0">{s.path}</span>
                              <Badge variant="outline" className="text-xs ml-2 shrink-0 whitespace-nowrap">{s.type}</Badge>
                            </div>
                            {s.description && <div className="text-xs text-muted-foreground truncate">{s.description}</div>}
                          </div>
                        ))}
                      </div>,
                      document.body
                    )
                  )}
                </div>
                {(externalErrors && externalErrors.length > 0 ? externalErrors : validationErrors).length > 0 && (
                  <div className="space-y-2">
                    {(externalErrors && externalErrors.length > 0 ? externalErrors : validationErrors).map((error, index) => (
                      <div key={index} className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-destructive">{error}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Conversation Instructions */}
          <Card className="relative overflow-hidden">
            <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Conversation Instructions
              </CardTitle>
              <CardDescription>
                These will instruct the agent on how to communicate with other agents, it the general tone of conversation and guidelines, this will be visible in the agents chat room during the game.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Label htmlFor="conversation-instructions">Conversation Instructions</Label>
                <Textarea
                  id="conversation-instructions"
                  value={conversationInstructions}
                  onChange={(e) => handleFieldChange("conversation", e.target.value)}
                  onKeyDown={onSystemPromptKeyDown}
                  onBlur={() => setShowSuggestions(false)}
                  placeholder="Always explain your reasoning step by step. Consider pot odds and opponent behavior..."
                  className="min-h-[120px]"
                  ref={conversationRef}
                />
              </div>
            </CardContent>
          </Card>

          {/* Exit Criteria */}
          <Card className="relative overflow-hidden">
            <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <StopCircle className="h-5 w-5" />
                Exit Criteria
              </CardTitle>
              <CardDescription>
                Define when your agent should stop playing or exit the game.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Label htmlFor="exit-criteria">Exit Criteria</Label>
                <Textarea
                  id="exit-criteria"
                  value={exitCriteria}
                  onChange={(e) => handleFieldChange("exit", e.target.value)}
                  onKeyDown={onSystemPromptKeyDown}
                  onBlur={() => setShowSuggestions(false)}
                  placeholder="Exit when chips fall below 100 or after 50 hands played..."
                  className="min-h-[100px]"
                  ref={exitRef}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Variables and Help */}
        <div className="space-y-6 min-h-0 pr-1">
          {/* Available Variables */}
          {mode === "advanced" && (
            <Card className="relative overflow-hidden">
              <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  Template Variables
                </CardTitle>
                <CardDescription>
                  Click to insert variables into your system prompt.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Search */}
                <div className="mb-3">
                  <Label htmlFor="var-search">Search variables</Label>
                  <input
                    id="var-search"
                    type="text"
                    className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                    placeholder="Filter..."
                    value={varSearch}
                    onChange={(e) => {
                      const q = e.target.value;
                      setVarSearch(q);
                      const ql = q.trim().toLowerCase();
                      const filtered = ql
                        ? availableVariables.filter(v => v.path.toLowerCase().includes(ql) || (v.description || "").toLowerCase().includes(ql))
                        : availableVariables;
                      setFilteredVariables(filtered);
                    }}
                  />
                </div>
                {loadingVariables ? (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-teal mx-auto mb-2"></div>
                    <p className="text-sm text-muted-foreground">Loading variables...</p>
                  </div>
                ) : (
                  <div className="space-y-2 overflow-y-auto max-h-64 sm:max-h-72 md:max-h-80 overflow-x-hidden">
                    {filteredVariables.map((variable) => (
                      <div
                        key={variable.path}
                        className="p-3 bg-muted/30 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => insertVariable(variable)}
                      >
                        <div className="flex items-center justify-between mb-1 gap-2 min-w-0">
                          <code className="text-sm font-mono text-brand-teal truncate flex-1 min-w-0">
                            $&#123;&#123;{variable.path}&#125;&#125;
                          </code>
                          <Badge variant="outline" className="text-xs shrink-0 whitespace-nowrap">
                            {variable.type}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mb-1 break-words">
                          {variable.description}
                        </p>
                        {variable.exampleValue && (
                          <p className="text-xs text-muted-foreground break-words">
                            <span className="font-medium">Example:</span> {JSON.stringify(variable.exampleValue)}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Tips */}
          <Card className="relative overflow-hidden">
            <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5" />
                Tips
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm text-muted-foreground">
                {mode === "advanced" && (
                  <div>
                    <p className="font-medium text-foreground mb-1">Template Variables</p>
                    <p>Use $&#123;&#123;variable.path&#125;&#125; syntax to access game state data in your prompts.</p>
                  </div>
                )}
                <div>
                  <p className="font-medium text-foreground mb-1">Be Specific</p>
                  <p>Clear, detailed instructions lead to better agent performance.</p>
                </div>
                <div>
                  <p className="font-medium text-foreground mb-1">Test Iteratively</p>
                  <p>Use the testing interface to refine your agent's behavior.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AgentInstructionsTab;
