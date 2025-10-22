import React from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FormAction {
  label: string;
  onClick: () => void | Promise<void>;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit' | 'reset';
  icon?: React.ReactNode;
}

interface FormActionsProps {
  actions: FormAction[];
  className?: string;
  alignment?: 'left' | 'center' | 'right' | 'between';
  spacing?: 'sm' | 'md' | 'lg';
  vertical?: boolean;
}

/**
 * FormActions provides a standardized way to display form action buttons
 */
export const FormActions: React.FC<FormActionsProps> = ({
  actions,
  className,
  alignment = 'right',
  spacing = 'md',
  vertical = false
}) => {
  const alignmentClasses = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end',
    between: 'justify-between'
  };

  const spacingClasses = {
    sm: vertical ? 'space-y-2' : 'space-x-2',
    md: vertical ? 'space-y-3' : 'space-x-3',
    lg: vertical ? 'space-y-4' : 'space-x-4'
  };

  return (
    <div
      className={cn(
        'flex',
        vertical ? 'flex-col' : 'flex-row flex-wrap',
        alignmentClasses[alignment],
        spacingClasses[spacing],
        className
      )}
    >
      {actions.map((action, index) => (
        <Button
          key={index}
          variant={action.variant || 'default'}
          size={action.size || 'default'}
          type={action.type || 'button'}
          disabled={action.disabled || action.loading}
          onClick={action.onClick}
          className={cn(
            action.variant === 'default' && 'button-primary'
          )}
        >
          {action.loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
              Loading...
            </>
          ) : (
            <>
              {action.icon && (
                <span className="mr-2">{action.icon}</span>
              )}
              {action.label}
            </>
          )}
        </Button>
      ))}
    </div>
  );
};

export default FormActions;
