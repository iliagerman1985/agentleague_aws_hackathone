import React from 'react';
import { ListOrdered } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface MoveEvent {
  id: string;
  text: string;
}

interface MovesCardProps {
  moves: MoveEvent[];
  scrollRef?: React.RefObject<HTMLDivElement>;
  className?: string;
  testId?: string;
}

export const MovesCard: React.FC<MovesCardProps> = ({
  moves,
  scrollRef,
  className = '',
  testId,
}) => {
  return (
    <Card className={`${className} bg-orange-50/50 dark:bg-card`} data-testid={testId}>
      <CardHeader className="pb-3 flex-shrink-0">
        <CardTitle className="text-lg flex items-center gap-2">
          <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-4 pb-4" ref={scrollRef}>
        {moves.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground text-xs">
            No moves yet.
          </div>
        ) : (
          <ol className="space-y-1 pl-4 list-decimal text-xs">
            {moves.map((m) => (
              <li key={m.id} className="leading-snug">{m.text}</li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
};

