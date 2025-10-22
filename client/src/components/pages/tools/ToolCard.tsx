import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { type Tool } from '@/services/toolsService';
import { Pencil, Trash2, Code, Clock } from 'lucide-react';

interface ToolCardProps {
  tool: Tool;
  onEdit: (tool: Tool) => void;
  onDelete: (tool: Tool) => void;
}

export const ToolCard: React.FC<ToolCardProps> = ({ tool, onEdit, onDelete }) => {
  return (
    <div className="item-card rounded-xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0))] p-5" data-testid="tool-card">
      <div className="flex items-start justify-between gap-3" data-testid="tool-card-header">
        <div className="flex items-center gap-3 min-w-0">
          <div className="card-icon w-10 h-10 rounded-full flex items-center justify-center shrink-0" data-testid="tool-card-icon">
            <span className="text-sm font-medium">
              {tool.displayName.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0">
            <div className="font-medium text-white truncate" data-testid="tool-card-name">{tool.displayName}</div>
            {tool.description && (
              <div className="text-sm text-gray-400 mt-1 line-clamp-2" data-testid="tool-card-description">{tool.description}</div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm" data-testid="tool-card-meta">
        <Badge
          variant="secondary"
          className="bg-primary/10 text-primary border-primary/20 flex items-center gap-1 px-2 py-0.5 text-[12px]"
        >
          <Code className="h-4 w-4" />
          <span>{tool.code.length} chars</span>
        </Badge>
        <div className="flex items-center gap-1 text-muted-foreground whitespace-nowrap" data-testid="tool-card-updated">
          <Clock className="h-4 w-4" />
          <span>{new Date(tool.updatedAt).toLocaleString()}</span>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3" data-testid="tool-card-actions">
        <Button variant="outline" size="sm" onClick={() => onEdit(tool)} data-testid="edit-tool-button">
          <Pencil className="h-4 w-4 mr-2" />
          Edit
        </Button>
        <Button variant="destructive" size="sm" onClick={() => onDelete(tool)} data-testid="delete-tool-button">
          <Trash2 className="h-4 w-4 mr-2" />
          Delete
        </Button>
      </div>
    </div>
  );
};

export default ToolCard;