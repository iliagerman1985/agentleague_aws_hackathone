import React from 'react';
import { Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface AnalysisEvent {
  roundNumber?: number;
  moveSan?: string;
  narrative?: string;
  bestMoveSan?: string;
  evaluationCp?: number;
  isBrilliant?: boolean;
  isGood?: boolean;
  isInaccuracy?: boolean;
  isMistake?: boolean;
  isBlunder?: boolean;
  // For replay page format
  fromSquare?: string;
  toSquare?: string;
  evaluation?: number;
}

interface AnalysisCardProps {
  analyses: AnalysisEvent[];
  scrollRef?: React.RefObject<HTMLDivElement>;
  className?: string;
  testId?: string;
}

export const AnalysisCard: React.FC<AnalysisCardProps> = ({
  analyses,
  scrollRef,
  className = '',
  testId,
}) => {
  return (
    <Card className={`${className} bg-emerald-50/50 dark:bg-card`} data-testid={testId}>
      <CardHeader className="pb-2 flex-shrink-0">
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className="w-5 h-5 text-brand-mint" /> Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-4 pb-4" ref={scrollRef}>
        {analyses.length > 0 ? (
          <div className="space-y-3">
            {analyses.map((analysis, idx) => (
              <div key={idx} className="space-y-2 pb-3 border-b last:border-b-0 last:pb-0">
                {/* Move header - support both formats */}
                <div className="font-medium text-xs">
                  {analysis.roundNumber && analysis.moveSan
                    ? `Move ${analysis.roundNumber}: ${analysis.moveSan}`
                    : analysis.fromSquare && analysis.toSquare
                    ? `${analysis.fromSquare} → ${analysis.toSquare}`
                    : 'Move'}
                </div>
                
                {/* Narrative */}
                {analysis.narrative && (
                  <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">
                    {analysis.narrative}
                  </div>
                )}
                
                {/* Evaluation badges */}
                <div className="flex flex-wrap gap-2 text-xs">
                  {analysis.bestMoveSan && (
                    <span className="rounded-md bg-muted px-2 py-0.5">Best: {analysis.bestMoveSan}</span>
                  )}
                  {typeof analysis.evaluationCp === 'number' && (
                    <span className="rounded-md bg-muted px-2 py-0.5">
                      Eval: {(analysis.evaluationCp / 100).toFixed(2)}
                    </span>
                  )}
                  {typeof analysis.evaluation === 'number' && (
                    <span className="rounded-md bg-muted px-2 py-0.5">
                      Eval: {(analysis.evaluation / 100).toFixed(2)}
                    </span>
                  )}
                  {analysis.isBrilliant && (
                    <span className="rounded-md bg-brand-mint/20 text-brand-mint px-2 py-0.5">Brilliant</span>
                  )}
                  {analysis.isGood && (
                    <span className="rounded-md bg-brand-mint/10 text-brand-mint px-2 py-0.5">Good</span>
                  )}
                  {analysis.isInaccuracy && (
                    <span className="rounded-md bg-amber-100 text-amber-700 px-2 py-0.5">Inaccuracy</span>
                  )}
                  {analysis.isMistake && (
                    <span className="rounded-md bg-orange-100 text-orange-700 px-2 py-0.5">Mistake</span>
                  )}
                  {analysis.isBlunder && (
                    <span className="rounded-md bg-red-100 text-red-700 px-2 py-0.5">Blunder</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground text-xs">
            No analysis yet.
          </div>
        )}
      </CardContent>
    </Card>
  );
};

