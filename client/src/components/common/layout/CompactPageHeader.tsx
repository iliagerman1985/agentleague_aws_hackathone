import React from "react";

interface CompactPageHeaderProps {
  back?: React.ReactNode;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

/**
 * CompactPageHeader
 * A slim, responsive page header that conserves vertical space on mobile and desktop.
 * - Mobile: ~48px tall, icon-only actions, subtitle hidden
 * - Desktop: slightly taller with small padding; subtitle shown
 */
export const CompactPageHeader: React.FC<CompactPageHeaderProps> = ({
  back,
  title,
  subtitle,
  actions,
  className,
}) => {
  return (
    <div className={`w-full px-3 py-2 md:px-6 md:py-3 ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          {back}
          <div className="min-w-0">
            <h1 className="text-lg md:text-xl font-semibold truncate">{title}</h1>
            {subtitle ? (
              <p className="hidden sm:block text-xs text-muted-foreground truncate">{subtitle}</p>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-2">{actions}</div>
      </div>
    </div>
  );
};

export default CompactPageHeader;

