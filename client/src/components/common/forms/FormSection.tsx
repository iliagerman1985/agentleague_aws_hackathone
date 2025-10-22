import React from 'react';
import { cn } from '@/lib/utils';

interface FormSectionProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  border?: boolean;
  background?: boolean;
}

/**
 * FormSection provides a standardized way to group form fields with optional title and description
 */
export const FormSection: React.FC<FormSectionProps> = ({
  title,
  description,
  children,
  className,
  headerClassName,
  contentClassName,
  border = true,
  background = true
}) => {
  return (
    <div
      className={cn(
        'space-y-4',
        border && 'border border-border rounded-lg',
        background && 'bg-card',
        (border || background) && 'p-6',
        className
      )}
    >
      {(title || description) && (
        <div className={cn('space-y-1', headerClassName)}>
          {title && (
            <h3 className="text-base font-semibold text-foreground">
              {title}
            </h3>
          )}
          {description && (
            <p className="text-sm text-muted-foreground">
              {description}
            </p>
          )}
        </div>
      )}
      
      <div className={cn('space-y-4', contentClassName)}>
        {children}
      </div>
    </div>
  );
};

export default FormSection;
