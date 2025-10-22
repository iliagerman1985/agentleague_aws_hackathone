import React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { CheckCircle, XCircle, Clock, AlertCircle, Pause } from 'lucide-react';

type StatusType = 'success' | 'error' | 'warning' | 'info' | 'pending' | 'idle' | 'running' | 'passed' | 'failed';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

/**
 * StatusBadge provides consistent styling for status indicators across the app
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'md',
  showIcon = true,
  className
}) => {
  const getStatusConfig = (status: StatusType) => {
    switch (status) {
      case 'success':
      case 'passed':
        return {
          color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
          icon: CheckCircle,
          defaultLabel: status === 'passed' ? 'PASSED' : 'SUCCESS'
        };
      case 'error':
      case 'failed':
        return {
          color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
          icon: XCircle,
          defaultLabel: status === 'failed' ? 'FAILED' : 'ERROR'
        };
      case 'warning':
        return {
          color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
          icon: AlertCircle,
          defaultLabel: 'WARNING'
        };
      case 'info':
        return {
          color: 'bg-brand-orange/10 text-brand-orange border border-brand-orange/20',
          icon: AlertCircle,
          defaultLabel: 'INFO'
        };
      case 'pending':
      case 'running':
        return {
          color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
          icon: Clock,
          defaultLabel: status === 'running' ? 'RUNNING' : 'PENDING'
        };
      case 'idle':
        return {
          color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
          icon: Pause,
          defaultLabel: 'IDLE'
        };
      default:
        return {
          color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
          icon: AlertCircle,
          defaultLabel: String(status).toUpperCase()
        };
    }
  };

  const config = getStatusConfig(status);
  const Icon = config.icon;

  const sizeClasses = {
    sm: {
      badge: 'text-xs px-2 py-1',
      icon: 'h-3 w-3'
    },
    md: {
      badge: 'text-sm px-2.5 py-1',
      icon: 'h-3.5 w-3.5'
    },
    lg: {
      badge: 'text-base px-3 py-1.5',
      icon: 'h-4 w-4'
    }
  };

  const classes = sizeClasses[size];

  return (
    <Badge
      className={cn(
        config.color,
        classes.badge,
        'font-semibold border-0 flex items-center gap-1',
        className
      )}
    >
      {showIcon && <Icon className={classes.icon} />}
      {label || config.defaultLabel}
    </Badge>
  );
};

export default StatusBadge;
