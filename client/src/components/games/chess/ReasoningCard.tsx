import React from 'react';
import { Brain, Wrench, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/common/Avatar';
import type { PlayerId } from '@/types/ids';

interface ToolCall {
  tool_name?: string;
  input?: any;
  output?: any;
}

interface ReasoningEvent {
  id: string;
  playerId: PlayerId;
  reasoning: string;
  toolCalls?: ToolCall[];
  isForfeit?: boolean;
}

interface PlayerInfo {
  name: string;
  avatarUrl?: string | null;
  avatarType?: string;
}

interface ReasoningCardProps {
  reasoningEvents: ReasoningEvent[];
  playerInfo: Record<string, PlayerInfo>;
  onShowAgentProfile?: (playerId: PlayerId) => void;
  onShowToolCalls?: (toolCalls: ToolCall[], agentName: string) => void;
  scrollRef?: React.RefObject<HTMLDivElement>;
  className?: string;
  testId?: string;
}

export const ReasoningCard: React.FC<ReasoningCardProps> = ({
  reasoningEvents,
  playerInfo,
  onShowAgentProfile,
  onShowToolCalls,
  scrollRef,
  className = '',
  testId,
}) => {
  return (
    <Card className={`${className} bg-cyan-50/50 dark:bg-card`} data-testid={testId}>
      <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
        <CardTitle className="text-lg flex items-center gap-2">
          <Brain className="w-5 h-5 text-brand-mint" /> Reasoning
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={scrollRef}>
        {reasoningEvents.length > 0 ? (
          <div className="space-y-3">
            {reasoningEvents.map((r) => {
              const player = playerInfo[r.playerId];
              return (
                <div key={r.id} className={`space-y-1 pb-3 border-b last:border-b-0 last:pb-0 ${r.isForfeit ? 'bg-red-50 dark:bg-red-950/20 -mx-2 px-2 py-1 rounded-md' : ''}`}>
                  <div className="flex items-center gap-2">
                    {r.isForfeit && <AlertTriangle className="w-4 h-4 text-red-500" />}
                    <div
                      className={onShowAgentProfile ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}
                      onClick={() => onShowAgentProfile?.(r.playerId)}
                    >
                      <Avatar
                        src={player?.avatarUrl}
                        fallback={player?.name || "Agent"}
                        size="lg"
                        className="flex-shrink-0"
                        type={player?.avatarType as any}
                      />
                    </div>
                    <div className={`font-medium text-xs ${r.isForfeit ? 'text-red-600 dark:text-red-400' : 'text-brand-teal'}`}>
                      {player?.name || "Agent"}
                      {r.isForfeit && " (Forfeit)"}
                    </div>
                  </div>
                  <div className={`whitespace-pre-wrap break-words text-xs leading-relaxed ${r.isForfeit ? 'text-red-700 dark:text-red-300 font-medium' : 'text-muted-foreground'}`}>
                    {r.reasoning}
                  </div>
                  {r.toolCalls && r.toolCalls.length > 0 && onShowToolCalls && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs mt-1"
                      onClick={() => onShowToolCalls(r.toolCalls!, player?.name || "Agent")}
                    >
                      <Wrench className="h-3 w-3 mr-1" />
                      Tools
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground text-xs">
            No reasoning yet
          </div>
        )}
      </CardContent>
    </Card>
  );
};

