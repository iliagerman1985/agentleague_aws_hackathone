import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { ResponsiveTableContainer } from "./ResponsiveTableContainer";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (item: T, index: number) => React.ReactNode;
  className?: string;
  headerClassName?: string;
  sortable?: boolean;
  sortFn?: (a: T, b: T) => number;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  headerClassName?: string;
  rowClassName?: string | ((item: T, index: number) => string);
  onRowClick?: (item: T, index: number) => void;
  striped?: boolean;
  hover?: boolean;
  minWidth?: number;
  defaultSortKey?: keyof T | string;
  defaultSortDirection?: 'asc' | 'desc';
}

/**
 * DataTable provides a reusable table component with consistent styling and sorting
 */
export function DataTable<T>({
  data,
  columns,
  loading = false,
  emptyMessage = 'No data available',
  className,
  headerClassName,
  rowClassName,
  onRowClick,
  striped = true,
  hover = true,
  minWidth,
  defaultSortKey,
  defaultSortDirection = 'asc'
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<keyof T | string | null>(defaultSortKey || null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(defaultSortDirection);

  const sortedData = useMemo(() => {
    if (!sortKey) return data;

    const column = columns.find(col => col.key === sortKey);
    if (!column) return data;

    const sorted = [...data].sort((a, b) => {
      // Use custom sort function if provided
      if (column.sortFn) {
        return sortDirection === 'asc' ? column.sortFn(a, b) : column.sortFn(b, a);
      }

      // Default sorting by key value
      const aValue = (a as any)[sortKey];
      const bValue = (b as any)[sortKey];

      if (aValue === bValue) return 0;
      if (aValue == null) return 1;
      if (bValue == null) return -1;

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortDirection === 'asc'
        ? aValue < bValue ? -1 : 1
        : aValue > bValue ? -1 : 1;
    });

    return sorted;
  }, [data, sortKey, sortDirection, columns]);

  const handleSort = (column: Column<T>) => {
    if (!column.sortable) return;

    if (sortKey === column.key) {
      // Toggle direction
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to ascending
      setSortKey(column.key);
      setSortDirection('asc');
    }
  };

  const getRowClassName = (item: T, index: number) => {
    // Use transition for smooth hover effects, no individual borders since we use divide-y
    let classes = 'transition-colors duration-200';

    // Remove striped backgrounds to avoid nested card appearance
    // The container already has bg-card, so rows should be transparent
    if (striped) {
      classes += index % 2 ? ' bg-muted/5' : ' bg-transparent';
    }

    if (hover) {
      classes += ' hover:bg-muted/10';
    }

    if (onRowClick) {
      classes += ' cursor-pointer';
    }

    if (typeof rowClassName === 'function') {
      classes += ' ' + rowClassName(item, index);
    } else if (rowClassName) {
      classes += ' ' + rowClassName;
    }

    return classes;
  };

  const getCellValue = (item: T, column: Column<T>, index: number) => {
    if (column.render) {
      return column.render(item, index);
    }

    const value = (item as any)[column.key];
    return value?.toString() || '';
  };

  const getSortIcon = (column: Column<T>) => {
    if (!column.sortable) return null;

    if (sortKey !== column.key) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }

    return sortDirection === 'asc'
      ? <ArrowUp className="h-3 w-3 ml-1" />
      : <ArrowDown className="h-3 w-3 ml-1" />;
  };

  if (loading) {
    return (
      <div className={cn('overflow-hidden rounded-xl border bg-card', className)}>
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={cn('overflow-hidden rounded-xl border bg-card', className)}>
        <div className="p-8 text-center">
          <p className="text-muted-foreground">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <ResponsiveTableContainer className={className} minWidth={minWidth}>
      <table className="w-full text-sm border-separate border-spacing-0">
        <thead>
          <tr className={cn('bg-muted/30 text-muted-foreground border-b border-border', headerClassName)}>
            {columns.map((column, index) => (
              <th
                key={index}
                className={cn(
                  'px-2 sm:px-4 py-1.5 sm:py-3 font-medium text-xs sm:text-sm',
                  column.sortable && 'cursor-pointer select-none hover:bg-muted/50 transition-colors',
                  column.headerClassName
                )}
                onClick={() => handleSort(column)}
              >
                <div className={cn('flex items-center', column.headerClassName?.includes('text-right') || column.headerClassName?.includes('justify-end') ? 'justify-end' : '')}>
                  {column.header}
                  {getSortIcon(column)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((item, index) => (
            <tr
              key={index}
              className={cn(getRowClassName(item, index), index > 0 && 'border-t border-border')}
              onClick={onRowClick ? () => onRowClick(item, index) : undefined}
            >
              {columns.map((column, colIndex) => (
                <td
                  key={colIndex}
                  className={cn('px-2 sm:px-4 py-1.5 sm:py-3', column.className)}
                >
                  {getCellValue(item, column, index)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </ResponsiveTableContainer>
  );
}

export default DataTable;
