import React from 'react';
import { cn } from '@/lib/utils';

type StatusType = 'success' | 'error' | 'warning' | 'info' | 'pending' | 'idle';

interface StatusIndicatorProps {
  status: StatusType;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  animated?: boolean;
}

/**
 * StatusIndicator provides a simple dot indicator for status
 */
export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  size = 'md',
  className,
  animated = false
}) => {
  const getStatusColor = (status: StatusType) => {
    switch (status) {
      case 'success':
        return 'bg-emerald-500';
      case 'error':
        return 'bg-red-500';
      case 'warning':
        return 'bg-amber-500';
      case 'info':
        return 'bg-brand-teal';
      case 'pending':
        return 'bg-amber-400';
      case 'idle':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  const sizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-3 w-3',
    lg: 'h-4 w-4'
  };

  return (
    <div
      className={cn(
        'rounded-full',
        getStatusColor(status),
        sizeClasses[size],
        animated && 'animate-pulse',
        className
      )}
    />
  );
};

export default StatusIndicator;
