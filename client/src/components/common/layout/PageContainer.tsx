import React from 'react';
import { cn } from '@/lib/utils';

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  background?: boolean;
  centered?: boolean; // Add vertical centering option
}

/**
 * PageContainer provides consistent padding and layout for all pages
 * Fixes the issue where content touches the edges of the screen
 */
export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className,
  maxWidth = 'full',
  padding = 'md',
  background = false,
  centered = false
}) => {
  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-full'
  };

  const paddingClasses = {
    none: '',
    sm: 'p-2 sm:p-3',
    md: 'p-4 sm:p-6 lg:p-8',
    lg: 'p-6 sm:p-8 lg:p-12'
  };

  return (
    <div
      className={cn(
        'w-full mx-auto',
        centered && 'min-h-[calc(100vh-5rem)] flex flex-col justify-center',
        maxWidthClasses[maxWidth],
        paddingClasses[padding],
        background && 'bg-background/50 backdrop-blur-sm rounded-lg border border-border/50',
        className
      )}
    >
      {children}
    </div>
  );
};

export default PageContainer;
