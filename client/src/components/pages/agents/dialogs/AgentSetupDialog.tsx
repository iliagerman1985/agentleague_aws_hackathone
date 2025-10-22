import React, { useEffect, useState } from "react";
import { FormDialog } from "@/components/common/dialogs/FormDialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  GameEnvironment,
  GameEnvironmentMetadata,
  getAvailableGameEnvironments,
  loadGameEnvironmentMetadata,
  getCachedGameEnvironmentMetadata,
} from "@/services/agentsService";
import { Bot, Gamepad2 } from "lucide-react";
import { getEnvironmentTheme } from "@/lib/environmentThemes";

interface AgentSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete: (data: { name: string; description: string; gameEnvironment: GameEnvironment }) => void;
  onCancel: () => void;
}

export const AgentSetupDialog: React.FC<AgentSetupDialogProps> = ({
  open,
  onOpenChange,
  onComplete,
  onCancel,
}) => {
  const [envMetadata, setEnvMetadata] = useState<Record<GameEnvironment, GameEnvironmentMetadata> | null>(getCachedGameEnvironmentMetadata());
  const [loadingEnv, setLoadingEnv] = useState<boolean>(false);
  // const [envError, setEnvError] = useState<string | null>(null);

  useEffect(() => {
    if (!envMetadata && !loadingEnv) {
      setLoadingEnv(true);
      loadGameEnvironmentMetadata()
        .then((data) => {
          setEnvMetadata(data);
        })
        .catch(() => {
        })
        .finally(() => setLoadingEnv(false));
    }
  }, [envMetadata, loadingEnv]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [gameEnvironment, setGameEnvironment] = useState<GameEnvironment | null>(null);

  const availableEnvironments = getAvailableGameEnvironments();

  const handleSubmit = () => {
    if (name.trim() && gameEnvironment) {
      onComplete({
        name: name.trim(),
        description: description.trim(),
        gameEnvironment,
      });
      // Reset form
      setName("");
      setDescription("");
      setGameEnvironment(null);
    }
  };

  const handleCancel = () => {
    // Reset form
    setName("");
    setDescription("");
    setGameEnvironment(null);
    onCancel();
  };

  const isValid = name.trim().length > 0 && gameEnvironment !== null;

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Create New Agent"
      description="Set up your AI agent's basic information and select the game environment."
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      submitLabel="Continue"
      submitDisabled={!isValid}
      size="lg"
    >
      <div className="space-y-6">
        {/* Agent Basic Info */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Bot className="h-5 w-5 text-brand-teal" />
            <h3 className="text-lg font-semibold text-foreground">Agent Information</h3>
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent-name">Agent Name *</Label>
            <Input
              id="agent-name"
              placeholder="Enter a name for your agent..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full"
              autoFocus
            />
            <p className="text-sm text-muted-foreground">
              Choose a descriptive name that helps you identify this agent.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent-description">Description (Optional)</Label>
            <Textarea
              id="agent-description"
              placeholder="Describe your agent's purpose or strategy..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full resize-none"
            />
            <p className="text-sm text-muted-foreground">
              Add notes about your agent's intended behavior or use case.
            </p>
          </div>
        </div>

        {/* Game Environment Selection */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Gamepad2 className="h-5 w-5 text-brand-teal" />
            <h3 className="text-lg font-semibold text-foreground">Game Environment</h3>
          </div>

          <div className="space-y-3">
            <Label>Select the game environment for your agent *</Label>
            <p className="text-sm text-muted-foreground mb-4">
              Choose the type of game your agent will play. This cannot be changed after creation.
            </p>

            {availableEnvironments.map((env) => {
              const metadata = envMetadata?.[env];
              if (!metadata) return null;
              const theme = getEnvironmentTheme(env);
              const EnvIcon = theme.icon;
              return (
                <div
                  key={env}
                  className={`relative p-4 border rounded-lg cursor-pointer transition-colors overflow-hidden ${
                    gameEnvironment === env
                      ? 'border-brand-teal bg-brand-teal/5'
                      : 'border-border hover:border-brand-teal/50'
                  }`}
                  onClick={() => setGameEnvironment(env)}
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
                      {gameEnvironment === env && (
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

        {/* Next Steps Info */}
        <div className="bg-muted/30 p-4 rounded-lg">
          <h4 className="font-medium text-foreground mb-2">Next Steps</h4>
          <p className="text-sm text-muted-foreground">
            After creating your agent, you'll configure its tools, instructions, and AI models
            to define how it plays and makes decisions.
          </p>
        </div>
      </div>
    </FormDialog>
  );
};
