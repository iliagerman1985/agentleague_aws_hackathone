import React from 'react';
import { TinyArea } from './TinyArea';

interface RatingChartProps {
  data: Array<{ value: number; timestamp: string }>;
  height?: number;
  color?: string;
}

/**
 * Simple rating progression chart showing rating changes over time
 */
export const RatingChart: React.FC<RatingChartProps> = ({
  data,
  height = 60,
  color = '#0891B2',
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No rating history available
      </div>
    );
  }

  // Transform data for TinyArea component
  const chartData = data.map((point) => point.value);

  return (
    <div style={{ height: `${height}px` }}>
      <TinyArea
        points={chartData}
        color={color}
      />
    </div>
  );
};

