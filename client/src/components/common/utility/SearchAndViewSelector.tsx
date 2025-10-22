import React from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { ViewSelector, type ViewType } from '@/components/common/utility/ViewSelector';

interface SearchAndViewSelectorProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  searchPlaceholder: string;
  viewType: ViewType;
  onViewChange: (view: ViewType) => void;
  rightSlot?: React.ReactNode; // optional right-side content (e.g., Filter button)
}

export const SearchAndViewSelector: React.FC<SearchAndViewSelectorProps> = ({
  searchQuery,
  onSearchChange,
  searchPlaceholder,
  viewType,
  onViewChange,
  rightSlot,
}) => {
  return (
    <div className="mb-6 w-full" data-testid="search-and-view-selector">
      <div className="flex items-center justify-between gap-2">
        <div className="relative flex-1 w-full max-w-full group" data-testid="search-container">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4 z-10 pointer-events-none transition-colors duration-200 group-hover:text-muted-foreground/80" />
          <Input
            placeholder={searchPlaceholder}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10 pr-4 w-full"
            data-adornment-start="true"
            data-testid="search-input"
          />
        </div>
        <div className="flex items-center gap-2 flex-shrink-0" data-testid="view-selector-container">
          <ViewSelector viewType={viewType} onViewChange={onViewChange} />
          {rightSlot}
        </div>
      </div>
    </div>
  );
};