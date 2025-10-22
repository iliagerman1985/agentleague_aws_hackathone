import React from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'default' | 'outline' | 'secondary';
  };
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * EmptyState provides a consistent way to display empty states across the app
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: {
      container: 'py-8',
      icon: 'h-8 w-8 mb-3',
      title: 'text-base',
      description: 'text-sm',
      spacing: 'space-y-2'
    },
    md: {
      container: 'py-12',
      icon: 'h-12 w-12 mb-4',
      title: 'text-lg',
      description: 'text-base',
      spacing: 'space-y-3'
    },
    lg: {
      container: 'py-16',
      icon: 'h-16 w-16 mb-6',
      title: 'text-xl',
      description: 'text-base',
      spacing: 'space-y-4'
    }
  };

  const classes = sizeClasses[size];

  return (
    <div className={cn(
      'text-center',
      classes.container,
      className
    )} data-testid="empty-state">
      <div className={cn('flex flex-col items-center', classes.spacing)} data-testid="empty-state-content">
        {icon && (
          <div className={cn(
            'text-muted-foreground',
            classes.icon
          )} data-testid="empty-state-icon">
            {icon}
          </div>
        )}

        <div className="space-y-2" data-testid="empty-state-text">
          <h3 className={cn(
            'font-semibold text-foreground',
            classes.title
          )} data-testid="empty-state-title">
            {title}
          </h3>

          {description && (
            <p className={cn(
              'text-muted-foreground max-w-md mx-auto',
              classes.description
            )} data-testid="empty-state-description">
              {description}
            </p>
          )}
        </div>

        {action && (
          <Button
            variant={action.variant || 'default'}
            onClick={action.onClick}
            className="mt-4"
            data-testid="empty-state-action"
          >
            {action.label}
          </Button>
        )}
      </div>
    </div>
  );
};

export default EmptyState;
