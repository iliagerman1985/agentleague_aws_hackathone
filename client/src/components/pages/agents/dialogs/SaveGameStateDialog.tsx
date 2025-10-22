import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { FormDialog } from '@/components/common';
import { Tag, X } from 'lucide-react';
import { type AgentId } from '@/types/ids';
import { api } from '@/lib/api';
import { type SaveGameStateRequest, GameEnvironment } from '@/services/agentsService';

interface SaveGameStateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId?: AgentId | null;
  environment?: GameEnvironment;
  gameState: Record<string, any>;
  initialName?: string;
  initialDescription?: string;
  onSaved?: (savedState: any) => void;
}

export const SaveGameStateDialog: React.FC<SaveGameStateDialogProps> = ({
  open,
  onOpenChange,
  agentId,
  environment,
  gameState,
  initialName,
  initialDescription,
  onSaved,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState(initialDescription ?? '');
  // Reset or prefill name and description when dialog opens
  React.useEffect(() => {
    if (open) {
      setName(initialName ?? '');
      setDescription(initialDescription ?? '');
    }
  }, [open, initialName, initialDescription]);

  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    setName('');
    setDescription('');
    setTags([]);
    setNewTag('');
    setError(null);
    onOpenChange(false);
  };

  const handleAddTag = () => {
    const trimmedTag = newTag.trim().toLowerCase();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (!agentId && !environment) {
      setError('Either agent or environment must be provided');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let savedState;

      if (agentId) {
        // Save via agent endpoint (will determine environment from agent)
        const request: SaveGameStateRequest = {
          name: name.trim(),
          description: description.trim() || undefined,
          gameState: gameState,
          tags,
        };
        savedState = await api.agents.saveGameState(agentId, request);
      } else if (environment) {
        // Save directly as test scenario with environment
        const testScenario = {
          name: name.trim(),
          description: description.trim() || undefined,
          environment,
          game_state: gameState,
          tags,
        };
        savedState = await api.agents.saveTestScenario(testScenario);
      }

      onSaved?.(savedState);
      handleClose();
    } catch (err: any) {
      console.error('Failed to save game state:', err);
      setError(err.message || 'Failed to save game state. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isValid = name.trim().length > 0;

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Save Game State"
      description="Save the current game state for future use in testing."
      onSubmit={handleSave}
      onCancel={handleClose}
      submitLabel="Save State"
      submitDisabled={!isValid}
      loading={loading}
      size="lg"
    >
      <div className="space-y-6">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Name Field */}
        <div className="space-y-2">
          <Label htmlFor="state-name" className="text-sm font-medium">
            Name <span className="text-red-500">*</span>
          </Label>
          <Input
            id="state-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Pre-flop with pocket aces"
            className={!name.trim() ? 'border-dashed border-brand-orange/60' : ''}
            maxLength={200}
          />
          <p className="text-xs text-muted-foreground">
            {name.length}/200 characters
          </p>
        </div>

        {/* Description Field */}
        <div className="space-y-2">
          <Label htmlFor="state-description" className="text-sm font-medium">
            Description
          </Label>
          <Textarea
            id="state-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description of the scenario..."
            className="min-h-[80px] resize-none"
            maxLength={500}
          />
          <p className="text-xs text-muted-foreground">
            {description.length}/500 characters
          </p>
        </div>

        {/* Tags Section */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Tags</Label>

          {/* Add Tag Input */}
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Tag className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Add a tag..."
                className="pl-10"
                maxLength={50}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddTag}
              disabled={!newTag.trim() || tags.includes(newTag.trim().toLowerCase())}
            >
              Add
            </Button>
          </div>

          {/* Current Tags */}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="flex items-center gap-1 px-2 py-1"
                >
                  {tag}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0 hover:bg-transparent"
                    onClick={() => handleRemoveTag(tag)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          )}

          {/* Suggested Tags */}
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">Suggested tags:</p>
            <div className="flex flex-wrap gap-2">
              {['testing', 'edge-case', 'tournament', 'cash-game', 'bluff', 'value-bet'].map((suggestedTag) => (
                <Button
                  key={suggestedTag}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => {
                    if (!tags.includes(suggestedTag)) {
                      setTags([...tags, suggestedTag]);
                    }
                  }}
                  disabled={tags.includes(suggestedTag)}
                >
                  {suggestedTag}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Game State Preview */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Game State Preview</Label>
          <Card className="p-3 bg-muted/40 border border-border max-h-40 overflow-y-auto">
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap">
              {JSON.stringify(gameState, null, 2)}
            </pre>
          </Card>
        </div>
      </div>
    </FormDialog>
  );
};
