import React from 'react';
import { Grid3x3, Table } from 'lucide-react';
import { Button } from '@/components/ui/button';

export type ViewType = 'grid' | 'table';

interface ViewSelectorProps {
  viewType: ViewType;
  onViewChange: (view: ViewType) => void;
  className?: string;
}

export const ViewSelector: React.FC<ViewSelectorProps> = ({ 
  viewType, 
  onViewChange, 
  className = '' 
}) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* View buttons */}
      <Button
        variant={viewType === 'table' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewChange('table')}
        className={`w-9 h-9 px-0 ${viewType === 'table' ? 'bg-primary text-white' : 'hover:bg-gray-800/50'}`}
        title="Table view"
      >
        <Table className="h-4 w-4" />
      </Button>

      <Button
        variant={viewType === 'grid' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewChange('grid')}
        className={`w-9 h-9 px-0 ${viewType === 'grid' ? 'bg-primary text-white' : 'hover:bg-gray-800/50'}`}
        title="Grid view"
      >
        <Grid3x3 className="h-4 w-4" />
      </Button>
    </div>
  );
};

export const usePersistentView = (key: string, defaultView: ViewType = 'grid'): [ViewType, (view: ViewType) => void] => {
  const [view, setView] = React.useState<ViewType>(() => {
    try {
      const stored = localStorage.getItem(`view-preference-${key}`);
      return stored ? (stored as ViewType) : defaultView;
    } catch {
      return defaultView;
    }
  });

  const handleViewChange = React.useCallback((newView: ViewType) => {
    setView(newView);
    try {
      localStorage.setItem(`view-preference-${key}`, newView);
    } catch {
      // Handle localStorage errors silently
    }
  }, [key]);

  return [view, handleViewChange];
};

export default { ViewSelector, usePersistentView };