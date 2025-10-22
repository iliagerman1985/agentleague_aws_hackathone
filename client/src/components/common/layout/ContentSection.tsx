import React from 'react';
import { cn } from '@/lib/utils';

interface ContentSectionProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  spacing?: 'sm' | 'md' | 'lg';
  background?: boolean;
  border?: boolean;
}

/**
 * ContentSection provides consistent spacing and styling for content sections
 */
export const ContentSection: React.FC<ContentSectionProps> = ({
  children,
  title,
  description,
  className,
  headerClassName,
  contentClassName,
  spacing = 'md',
  background = true,
  border = true
}) => {
  const spacingClasses = {
    sm: 'space-y-3',
    md: 'space-y-4',
    lg: 'space-y-6'
  };

  return (
    <div
      className={cn(
        'rounded-lg',
        background && 'bg-card',
        border && 'border border-border',
        spacing !== 'sm' && 'p-6',
        spacing === 'sm' && 'p-4',
        className
      )}
    >
      {(title || description) && (
        <div className={cn('mb-6', headerClassName)}>
          {title && (
            <h2 className="text-lg font-semibold text-foreground mb-2">
              {title}
            </h2>
          )}
          {description && (
            <p className="text-muted-foreground">
              {description}
            </p>
          )}
        </div>
      )}
      
      <div className={cn(spacingClasses[spacing], contentClassName)}>
        {children}
      </div>
    </div>
  );
};

export default ContentSection;
