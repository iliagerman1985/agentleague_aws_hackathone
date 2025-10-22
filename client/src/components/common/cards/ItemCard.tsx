import React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { getEnvironmentTheme } from "@/lib/environmentThemes";

export interface ItemCardProps {
  title: string;
  description?: string;
  icon?: React.ReactNode; // optional icon to display in header
  iconContainerClassName?: string; // optional className for icon container
  headerBadge?: React.ReactNode;
  belowTitle?: React.ReactNode; // optional content directly under the title
  topRight?: React.ReactNode; // right-aligned row below the header (e.g., date)
  bottomLeft?: React.ReactNode; // bottom-left of the body (e.g., env badge or char count)
  bottomRight?: React.ReactNode; // bottom-right of the body (optional)
  meta?: React.ReactNode; // legacy: full-width bottom row
  features?: React.ReactNode; // optional chips/extra
  actions?: React.ReactNode; // buttons
  onClick?: () => void;
  clickable?: boolean;
  size?: "sm" | "md" | "lg"; // visual density/size
  environment?: string; // game environment for themed styling
  showEnvironmentArt?: boolean; // whether to show environment background art
  backgroundImage?: string; // optional background image URL (takes precedence over environment art)
  backgroundImageOpacity?: number; // transparency of background image
  backgroundImageGrayscale?: boolean; // whether to apply grayscale filter to background image
}

export const ItemCard: React.FC<ItemCardProps> = ({
  title,
  description,
  icon,
  iconContainerClassName,
  headerBadge,
  belowTitle,
  topRight,
  bottomLeft,
  bottomRight,
  meta,
  features,
  actions,
  onClick,
  clickable,
  size = "md",
  environment,
  showEnvironmentArt = true,
  backgroundImage,
  backgroundImageOpacity = 0.25,
  backgroundImageGrayscale = false,
}) => {
  const isLg = size === "lg";

  // Fixed heights per breakpoint to keep size constant per view type
  const heightCls =
    size === "lg"
      ? "h-[320px] sm:h-[344px] xl:h-[368px]"
      : size === "sm"
      ? "h-[180px] sm:h-[192px] xl:h-[200px]"
      : "h-[210px] sm:h-[230px] xl:h-[240px]"; // md default

  const descClamp = isLg ? "line-clamp-3" : "line-clamp-2";

  // Get environment theme for styling
  const envTheme = environment ? getEnvironmentTheme(environment) : null;
  const hasEnvTheme = envTheme && showEnvironmentArt && !backgroundImage;

  return (
    <Card
      className={
        "item-card bg-card border rounded-xl flex flex-col overflow-hidden relative " +
        heightCls +
        " " +
        (clickable
          ? "cursor-pointer"
          : "")
      }
      onClick={onClick}
      data-testid="item-card"
    >
      {/* Background layers */}
      {backgroundImage && (
        <div className="absolute inset-0 rounded-xl pointer-events-none select-none overflow-hidden" aria-hidden>
          {/* Solid background layer to prevent transparency squares */}
          <div className="absolute inset-0 bg-card" />
          {/* Image layer */}
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `url(${backgroundImage})`,
              backgroundRepeat: "no-repeat",
              backgroundPosition: "center",
              backgroundSize: "cover",
              opacity: backgroundImageOpacity,
              filter: backgroundImageGrayscale ? "grayscale(30%)" : "none",
            }}
          />
          {/* Very subtle overlay for text readability - only visible in light theme */}
          <div className="absolute inset-0 bg-gradient-to-b from-background/10 via-background/5 to-background/15" />
        </div>
      )}
      {hasEnvTheme && (
        <EnvironmentBackground
          environment={environment}
          className="absolute inset-0 rounded-xl"
          opacity={environment?.toLowerCase() === 'texas_holdem' ? 0.22 : environment?.toLowerCase() === 'chess' ? 0.10 : 0.15}
        />
      )}
      <CardHeader className={(isLg ? "pb-3" : "pb-2") + " relative z-10"}>
        <div className="flex items-start justify-between gap-3" data-testid="item-card-header">
          <div className="flex items-start gap-3 min-w-0">
            {icon && (
              <div className={iconContainerClassName || "bg-primary/10 text-primary flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full"}>
                {icon}
              </div>
            )}
            <div className="min-w-0">
              <CardTitle className={(isLg ? "text-xl" : "text-lg") + " text-foreground truncate font-bold"} data-testid="item-card-title">
                {title}
              </CardTitle>
              {belowTitle && <div className="mt-2" data-testid="item-card-below-title">{belowTitle}</div>}
            </div>
          </div>
          {headerBadge}
        </div>
      </CardHeader>

      <CardContent className={(isLg ? "space-y-4" : "space-y-3") + " flex-1 flex flex-col pb-2 sm:pb-3 relative z-10"} data-testid="item-card-content">
        {topRight && (
          <div className="-mt-1 mb-1 flex items-center justify-end text-xs sm:text-sm text-muted-foreground" data-testid="item-card-top-right">
            {topRight}
          </div>
        )}

        <div className="flex-1 flex flex-col justify-center gap-2 sm:gap-3 overflow-hidden" data-testid="item-card-main-content">
          {description && (
            <p className={"text-sm text-foreground font-medium " + descClamp} data-testid="item-card-description">{description}</p>
          )}

          {/* Feature list can vary; clip overflow to keep height constant */}
          {features && <div className="overflow-hidden" data-testid="item-card-features">{features}</div>}
        </div>

        {(bottomLeft || bottomRight) ? (
          <div className="mt-auto pt-1.5 sm:pt-2 flex items-center justify-between text-sm font-medium" data-testid="item-card-bottom-row">
            <div className="min-w-0" data-testid="item-card-bottom-left">{bottomLeft}</div>
            <div className="shrink-0" data-testid="item-card-bottom-right">{bottomRight}</div>
          </div>
        ) : (
          meta && (
            <div className="mt-auto pt-1.5 sm:pt-2 flex items-center justify-between text-sm font-medium" data-testid="item-card-meta">{meta}</div>
          )
        )}
      </CardContent>

      {actions && (
        <CardFooter className="mt-auto pt-2 sm:pt-4 border-t border-border/50 flex items-center justify-center w-full gap-3 relative z-10 bg-card backdrop-blur-sm" data-testid="item-card-actions">
          {actions}
        </CardFooter>
      )}
    </Card>
  );
};

export default ItemCard;
