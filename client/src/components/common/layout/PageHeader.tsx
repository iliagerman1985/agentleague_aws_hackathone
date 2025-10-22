import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, children }) => {
  return (
    <div className="flex items-center justify-between gap-3 mb-6">
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-0 sm:mb-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-full md:max-w-none md:whitespace-normal">{title}</h1>
        <p className="hidden sm:block text-muted-foreground text-lg">{subtitle}</p>
      </div>
      {children && <div className="flex items-center gap-3">{children}</div>}
    </div>
  );
};
