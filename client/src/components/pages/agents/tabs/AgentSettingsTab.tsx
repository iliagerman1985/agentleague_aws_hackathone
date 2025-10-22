import React, { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { Badge } from "@/components/ui/badge";
import { LLMProviderSelector } from "@/components/llm/LLMProviderSelector";
import { GameEnvironment, getGameEnvironmentMetadata, getAvailableGameEnvironments, loadGameEnvironmentMetadata, type GameEnvironmentMetadata } from "@/services/agentsService";
import { Bot, Zap, RotateCcw } from "lucide-react";
import { LLMProvider } from "@/lib/api";
import { getEnvironmentTheme } from "@/lib/environmentThemes";
import { AvatarUpload } from "@/components/common/AvatarUpload";

interface ValidationError {
  field: string;
  tab: string;
  label: string;
}

interface AgentSettingsTabProps {
  name: string;
  description: string;
  gameEnvironment: GameEnvironment;
  selectedProvider: LLMProvider | null;
  autoReenter: boolean;
  maxIterations: number;
  isNew: boolean;
  currentAvatar?: string | null;
  uploadingAvatar?: boolean;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onGameEnvironmentChange: (value: GameEnvironment) => void;
  onProviderChange: (value: LLMProvider | null) => void;
  onAutoReenterChange: (value: boolean) => void;
  onMaxIterationsChange: (value: number) => void;
  onAvatarUpload: (file: File) => Promise<void>;
  onAvatarRemove: () => Promise<void>;
  validationErrors?: ValidationError[];
  title?: string;
  showProvider?: boolean;
  showAutoReenter?: boolean;
  showMaxIterations?: boolean;
  showBasicSettings?: boolean;
}

export const AgentSettingsTab: React.FC<AgentSettingsTabProps> = ({
  name,
  description,
  gameEnvironment,
  selectedProvider,
  autoReenter,
  maxIterations,
  isNew,
  currentAvatar,
  uploadingAvatar,
  onNameChange,
  onDescriptionChange,
  onGameEnvironmentChange,
  onProviderChange,
  onAutoReenterChange,
  onMaxIterationsChange,
  onAvatarUpload,
  onAvatarRemove,
  validationErrors = [],
  title = "Agent Settings",
  showProvider = true,
  showAutoReenter = true,
  showMaxIterations = true,
  showBasicSettings = true,
}) => {
  const availableEnvironments = getAvailableGameEnvironments();
  const visibleEnvironments = isNew ? availableEnvironments : [gameEnvironment];
  const [environmentMetadata, setEnvironmentMetadata] = useState<GameEnvironmentMetadata>(() => getGameEnvironmentMetadata(gameEnvironment));

  // Load environment metadata from backend
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        await loadGameEnvironmentMetadata();
        // Update the metadata after loading from backend
        const updatedMetadata = getGameEnvironmentMetadata(gameEnvironment);
        setEnvironmentMetadata(updatedMetadata);
        console.log('Loaded environment metadata for', gameEnvironment, ':', updatedMetadata);
      } catch (error) {
        console.error('Failed to load environment metadata:', error);
        // Keep using the current metadata if loading fails
      }
    };

    loadMetadata();
  }, [gameEnvironment]);

  const hasNameError = validationErrors.some(e => e.field === 'name');
  const hasProviderError = validationErrors.some(e => e.field === 'provider');

  return (
    <div className="space-y-6">
      {/* Header - only show for non-Profile tabs */}
      {title !== "Agent Details" && (
        <div>
          <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
          <p className="text-muted-foreground">
            Configure your agent's basic information, environment, and execution parameters.
          </p>
        </div>
      )}

      {/* Basic Settings - only show if showBasicSettings is true */}
      {showBasicSettings && (
        <Card className="relative overflow-hidden">
        <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            {title === "Agent Details" ? "Agent Details" : "Basic Settings"}
          </CardTitle>
          <CardDescription>
            {title === "Agent Details"
              ? "Agent name, description, and visual identity."
              : "Agent name, description, environment, and execution limits."
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Avatar and Name/Description Section */}
          <div className="grid grid-cols-1 md:grid-cols-[140px_1fr] gap-4 items-start">
            {/* Avatar Upload */}
            <div className="flex justify-center md:justify-start md:self-center">
              <AvatarUpload
                currentAvatar={currentAvatar}
                onUpload={onAvatarUpload}
                onRemove={currentAvatar ? onAvatarRemove : undefined}
                canRemove={Boolean(currentAvatar)}
                uploading={uploadingAvatar}
                fallback={name || "Agent"}
                size="5xl"
                showBorder={true}
                showHelperText={false}
                showCameraButton={true}
              />
            </div>

            {/* Name and Description */}
            <div className="space-y-4 flex-1 min-w-0">
              <div className="space-y-2">
                <Label htmlFor="agent-name" className={hasNameError ? "text-destructive" : undefined}>
                  Agent Name *
                </Label>
                <Input
                  id="agent-name"
                  value={name}
                  onChange={(e) => onNameChange(e.target.value)}
                  placeholder="My Poker Agent"
                  required
                  aria-invalid={hasNameError}
                  className={hasNameError ? "border-destructive focus-visible:ring-destructive" : (!name.trim() ? "border-dashed border-brand-orange/60" : undefined)}
                />
                {hasNameError ? (
                  <p className="text-xs text-destructive mt-1">Agent name is required</p>
                ) : !name.trim() && (
                  <p className="text-xs text-muted-foreground mt-1">Give your agent a friendly name to identify it.</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="agent-description">Description</Label>
                <Textarea
                  id="agent-description"
                  value={description}
                  onChange={(e) => onDescriptionChange(e.target.value)}
                  placeholder="A strategic poker agent that focuses on maximizing long-term profits..."
                  rows={3}
                />
              </div>
            </div>
          </div>

          {title !== "Agent Details" && (
            <div className="space-y-2">
              <Label htmlFor="game-environment">Game Environment *</Label>
              <div className="space-y-2">
                {visibleEnvironments.map((env) => {
                  const metadata = getGameEnvironmentMetadata(env);
                  const theme = getEnvironmentTheme(env);
                  const EnvIcon = theme.icon;
                  return (
                    <div
                      key={env}
                      className={`relative p-2 border rounded-lg cursor-pointer transition-colors overflow-hidden ${
                        gameEnvironment === env
                          ? 'border-brand-teal bg-brand-teal/5'
                          : 'border-border hover:border-brand-teal/50'
                      } ${!isNew ? 'opacity-50 cursor-not-allowed' : ''}`}
                      onClick={() => isNew && onGameEnvironmentChange(env)}
                    >
                      {/* Environment-themed background gradient */}
                      <div
                        className="absolute inset-0 pointer-events-none"
                        style={{
                          background: `linear-gradient(to bottom right, ${theme.colors.primary}15, ${theme.colors.accent}10, transparent)`,
                        }}
                      />

                      <div className="relative z-10">
                        <div className="flex items-center justify-between mb-1.5">
                          <h4 className="font-medium text-foreground flex items-center gap-2 text-sm">
                            <span className="h-4 w-4 flex items-center" style={{ color: theme.colors.primary }}>
                              <EnvIcon />
                            </span>
                            {metadata.displayName}
                          </h4>
                          {gameEnvironment === env && (
                            <Badge className="bg-brand-teal text-white text-xs">Selected</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">{metadata.description}</p>
                        <div className="flex flex-wrap gap-1.5">
                          <Badge variant="outline" className="text-xs py-0 h-5">
                            {metadata.minPlayers}-{metadata.maxPlayers} players
                          </Badge>
                          {metadata.hasBetting && (
                            <Badge variant="outline" className="text-xs py-0 h-5">Betting</Badge>
                          )}
                          {metadata.isTurnBased && (
                            <Badge variant="outline" className="text-xs py-0 h-5">Turn-based</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              {!isNew && (
                <p className="text-xs text-muted-foreground">
                  Game environment cannot be changed after creation.
                </p>
              )}
            </div>
          )}

          {/* Execution Parameters */}
          {(showMaxIterations || (showAutoReenter && environmentMetadata.allowAutoReenter)) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {showMaxIterations && (
                <div className="space-y-2">
                  <Label htmlFor="max-iterations" className="flex items-center gap-2">
                    <RotateCcw className="h-4 w-4" />
                    Max Iterations
                  </Label>
                  <Input
                    id="max-iterations"
                    type="number"
                    min="1"
                    max="10"
                    value={maxIterations}
                    onChange={(e) => {
                      const n = parseInt(e.target.value || "10");
                      const clamped = Math.max(1, Math.min(10, Number.isNaN(n) ? 10 : n));
                      onMaxIterationsChange(clamped);
                    }}
                  />
                  <p className="text-sm text-muted-foreground">
                    Maximum tool iterations per decision (1-10)
                  </p>
                </div>
              )}

              {showAutoReenter && environmentMetadata.allowAutoReenter && (
                <div className="space-y-2">
                  <Label htmlFor="auto-reenter" className="flex items-center gap-2">
                    Auto re-enter
                  </Label>
                  <div className="flex items-center justify-between h-10 px-3 border rounded-lg bg-muted/30">
                    <p className="text-sm text-muted-foreground">
                      {gameEnvironment === GameEnvironment.TEXAS_HOLDEM
                        ? "Auto re-enter with available credits"
                        : "Auto re-enter when eliminated"}
                    </p>
                    <Switch
                      id="auto-reenter"
                      checked={autoReenter}
                      onCheckedChange={onAutoReenterChange}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {gameEnvironment === GameEnvironment.TEXAS_HOLDEM
                      ? "Agent will auto re-enter as long as there are credits available. It will not auto re-buy more credits."
                      : "Automatically re-enter the game when your agent is eliminated or the game ends."}
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {/* LLM Configuration */}
      {showProvider && (
        <Card className="relative overflow-hidden">
          <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              LLM Configuration
            </CardTitle>
            <CardDescription>
              Select the LLM provider for your agent.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className={hasProviderError ? "text-destructive" : undefined}>
                LLM Provider *
              </Label>
              <p className="text-sm text-muted-foreground mb-2">
                Choose the provider that will power your agent's reasoning
              </p>
              <LLMProviderSelector
                selectedProvider={selectedProvider}
                onProviderChange={onProviderChange}
                placeholder="Select LLM provider..."
                className={hasProviderError ? "border border-destructive rounded-lg p-2 bg-destructive/10 w-full" : (!selectedProvider ? "border border-dashed border-brand-orange/60 rounded-lg p-2 bg-muted/30 w-full" : "w-full")}
              />
              {hasProviderError ? (
                <p className="text-xs text-destructive mt-1">LLM provider selection is required</p>
              ) : !selectedProvider && (
                <p className="text-xs text-muted-foreground mt-1">Select an LLM provider to enable your agent's capabilities.</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AgentSettingsTab;
