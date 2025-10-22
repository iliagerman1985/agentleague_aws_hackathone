import React from "react";
import { Button } from "@/components/ui/button";
import { DataTable } from "./DataTable";
import { cn } from "@/lib/utils";

interface ActionButton<T> {
  label: string;
  onClick: (item: T, index: number) => void;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  disabled?: (item: T, index: number) => boolean;
  className?: string;
  icon?: React.ReactNode;
}

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (item: T, index: number) => React.ReactNode;
  className?: string;
  headerClassName?: string;
  sortable?: boolean;
  sortFn?: (a: T, b: T) => number;
}

interface ActionTableProps<T> {
  data: T[];
  columns: Column<T>[];
  actions: ActionButton<T>[];
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  headerClassName?: string;
  rowClassName?: string | ((item: T, index: number) => string);
  onRowClick?: (item: T, index: number) => void;
  striped?: boolean;
  hover?: boolean;
  actionsHeader?: string;
  actionsClassName?: string;
  minWidth?: number;
  defaultSortKey?: keyof T | string;
  defaultSortDirection?: 'asc' | 'desc';
}

/**
 * ActionTable extends DataTable with action buttons for each row
 */
export function ActionTable<T>({
  data,
  columns,
  actions,
  loading = false,
  emptyMessage = 'No data available',
  className,
  headerClassName,
  rowClassName,
  onRowClick,
  striped = true,
  hover = true,
  actionsHeader = 'Actions',
  actionsClassName = 'text-right',
  minWidth,
  defaultSortKey,
  defaultSortDirection
}: ActionTableProps<T>) {
  // Only add actions column if there are actions to display
  const columnsWithActions = actions.length > 0 ? [
    ...columns,
    {
      key: '__actions__' as keyof T,
      header: actionsHeader,
      headerClassName: cn('text-right justify-end w-[60px] sm:w-auto', actionsClassName),
      className: cn('w-[60px] sm:w-auto', actionsClassName),
      render: (item: T, index: number) => (
        <div className="flex items-center gap-1 sm:gap-2 justify-end shrink-0 h-6 sm:h-auto">
          {actions.map((action, actionIndex) => {
            const isDisabled = action.disabled ? action.disabled(item, index) : false;

            return (
              <Button
                key={actionIndex}
                variant={action.variant || "outline"}
                size={action.size || "sm"}
                onClick={(e) => {
                  e.stopPropagation(); // Prevent row click when clicking action
                  action.onClick(item, index);
                }}
                disabled={isDisabled}
                className={cn(
                  "h-6 w-6 sm:h-9 sm:w-auto sm:px-3 justify-center rounded-full sm:rounded-md p-0 sm:p-2 shrink-0",
                  action.className
                )}
                title={action.label}
                aria-label={action.label}
              >
                {action.icon && (
                  <span className="sm:mr-1 scale-75 sm:scale-100">{action.icon}</span>
                )}
                <span className="hidden sm:inline">{action.label}</span>
              </Button>
            );
          })}
        </div>
      )
    }
  ] : columns;

  return (
    <DataTable
      data={data}
      columns={columnsWithActions}
      loading={loading}
      emptyMessage={emptyMessage}
      className={className}
      headerClassName={headerClassName}
      rowClassName={rowClassName}
      onRowClick={onRowClick}
      striped={striped}
      hover={hover}
      minWidth={minWidth}
      defaultSortKey={defaultSortKey}
      defaultSortDirection={defaultSortDirection}
    />
  );
}

export default ActionTable;
