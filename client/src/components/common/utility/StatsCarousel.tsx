import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import CountUp from '@/components/CountUp';

export interface StatItem {
  icon: React.ReactNode;
  label: string;
  value: string;
  description: string;
  variant?: "teal" | "orange" | "mint" | "purple" | "blue" | "cyan" | "indigo" | "emerald" | "yellow" | "red" | "sky" | "green" | "amber";
}

interface StatsCarouselProps {
  stats: StatItem[];
  autoRotateInterval?: number;
}

// Light-mode tinted variants (fall back to neutral in dark mode)
const VARIANTS = {
  teal:   { card: "from-brand-teal/10 via-white to-brand-teal/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-brand-teal/25",   icon: "from-brand-teal/20 to-brand-teal/5 dark:from-primary/15 dark:to-primary/5 ring-brand-teal/30" },
  orange: { card: "from-brand-orange/10 via-white to-brand-orange/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-brand-orange/25", icon: "from-brand-orange/20 to-brand-orange/5 dark:from-primary/15 dark:to-primary/5 ring-brand-orange/30" },
  mint:   { card: "from-brand-mint/10 via-white to-brand-mint/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-brand-mint/25",   icon: "from-brand-mint/20 to-brand-mint/5 dark:from-primary/15 dark:to-primary/5 ring-brand-mint/30" },
  purple: { card: "from-purple-500/10 via-white to-purple-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-purple-300/40",     icon: "from-purple-500/20 to-purple-500/5 dark:from-primary/15 dark:to-primary/5 ring-purple-300/40" },
  cyan:   { card: "from-cyan-500/10 via-white to-cyan-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-cyan-300/40",         icon: "from-cyan-500/20 to-cyan-500/5 dark:from-primary/15 dark:to-primary/5 ring-cyan-300/40" },
  blue:   { card: "from-blue-500/10 via-white to-blue-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-blue-300/40",         icon: "from-blue-500/20 to-blue-500/5 dark:from-primary/15 dark:to-primary/5 ring-blue-300/40" },
  green:  { card: "from-green-500/10 via-white to-green-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-green-300/40",       icon: "from-green-500/20 to-green-500/5 dark:from-primary/15 dark:to-primary/5 ring-green-300/40" },
  yellow: { card: "from-yellow-500/10 via-white to-yellow-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-yellow-300/40",     icon: "from-yellow-500/20 to-yellow-500/5 dark:from-primary/15 dark:to-primary/5 ring-yellow-300/40" },
  red:    { card: "from-red-500/10 via-white to-red-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-red-300/40",             icon: "from-red-500/20 to-red-500/5 dark:from-primary/15 dark:to-primary/5 ring-red-300/40" },
  sky:    { card: "from-sky-500/10 via-white to-sky-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-sky-300/40",             icon: "from-sky-500/20 to-sky-500/5 dark:from-primary/15 dark:to-primary/5 ring-sky-300/40" },
  amber:  { card: "from-amber-500/10 via-white to-amber-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-amber-300/40",       icon: "from-amber-500/20 to-amber-500/5 dark:from-primary/15 dark:to-primary/5 ring-amber-300/40" },
  indigo: { card: "from-indigo-500/10 via-white to-indigo-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-indigo-300/40",     icon: "from-indigo-500/20 to-indigo-500/5 dark:from-primary/15 dark:to-primary/5 ring-indigo-300/40" },
  emerald:{ card: "from-emerald-500/10 via-white to-emerald-500/5 dark:from-card/95 dark:via-card/90 dark:to-card/95 border-emerald-300/40",   icon: "from-emerald-500/20 to-emerald-500/5 dark:from-primary/15 dark:to-primary/5 ring-emerald-300/40" },
} as const;

type VariantKey = keyof typeof VARIANTS;
const pick = (v?: VariantKey) => VARIANTS[v ?? "teal"];

export const StatsCarousel: React.FC<StatsCarouselProps> = ({
  stats,
  autoRotateInterval = 3000
}) => {
  const [currentStatIndex, setCurrentStatIndex] = useState(0);

  // Auto-rotate carousel (only on mobile)
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStatIndex((prev) => (prev + 1) % stats.length);
    }, autoRotateInterval);

    return () => clearInterval(interval);
  }, [stats.length, autoRotateInterval]);

  const nextStat = () => {
    setCurrentStatIndex((prev) => (prev + 1) % stats.length);
  };

  const prevStat = () => {
    setCurrentStatIndex((prev) => (prev - 1 + stats.length) % stats.length);
  };

  if (!stats.length) {
    return null;
  }

  const getGridClasses = () => {
    switch (stats.length) {
      case 1:
        return "hidden lg:flex lg:justify-center";
      case 2:
        return "hidden lg:grid lg:grid-cols-2 lg:max-w-2xl lg:mx-auto gap-4 sm:gap-6";
      case 3:
        return "hidden lg:grid lg:grid-cols-3 lg:max-w-4xl lg:mx-auto gap-4 sm:gap-6";
      case 4:
      default:
        return "hidden lg:grid lg:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6 w-full";
    }
  };

  return (
    <div className="relative mb-6 sm:mb-8 w-full hidden lg:block">
      {/* Desktop: Show all cards in a grid */}
      <div className={getGridClasses()}>
        {stats.map((stat, index) => {
          const c = pick(stat.variant as VariantKey);
          return (
            <div key={index} className={`item-card bg-gradient-to-br ${c.card} backdrop-blur-sm border rounded-xl p-4 sm:p-6 shadow-sm`}>
              <div className="flex flex-col items-center text-center">
                <div className={`card-icon w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br ${c.icon} flex items-center justify-center flex-shrink-0 mb-3 sm:mb-4 shadow-inner ring-1`}>
                  {stat.icon}
                </div>
                <div>
                  <p className="text-muted-foreground text-sm sm:text-base font-medium">
                    {stat.label}
                  </p>
                  <p className="text-foreground text-2xl sm:text-3xl font-bold bg-gradient-to-br from-foreground to-foreground/80 bg-clip-text">
                    <CountUp from={0} to={parseFloat(stat.value.replace(/,/g, '')) || 0} duration={1} separator="," />
                  </p>
                  <p className="text-muted-foreground text-xs sm:text-sm">
                    {stat.description}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile: Show carousel */}
      <div className={`lg:hidden item-card bg-gradient-to-br ${pick(stats[currentStatIndex].variant as VariantKey).card} backdrop-blur-sm border rounded-xl p-5 sm:p-6 shadow-sm`}>
        <div className="relative flex items-center justify-center text-center">
          <button
            onClick={prevStat}
            className="absolute left-2 top-1/2 -translate-y-1/2 p-2.5 rounded-full hover:bg-accent transition-colors"
            aria-label="Previous stat"
          >
            <ChevronLeft className="h-6 w-6 text-muted-foreground" />
          </button>

          <div className="flex flex-col items-center justify-center w-full">
            <div className={`card-icon w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br ${pick(stats[currentStatIndex].variant as VariantKey).icon} flex items-center justify-center mb-3 sm:mb-4 shadow-inner ring-1`}>
              {stats[currentStatIndex].icon}
            </div>
            <p className="text-muted-foreground text-base sm:text-lg font-medium">{stats[currentStatIndex].label}</p>
            <p className="text-foreground text-4xl sm:text-5xl font-bold bg-gradient-to-br from-foreground to-foreground/80 bg-clip-text">
              <CountUp from={0} to={parseFloat(stats[currentStatIndex].value.replace(/,/g, '')) || 0} duration={1} separator="," />
            </p>
            <p className="text-muted-foreground text-sm sm:text-base">{stats[currentStatIndex].description}</p>
          </div>

          <button
            onClick={nextStat}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 rounded-full hover:bg-accent transition-colors"
            aria-label="Next stat"
          >
            <ChevronRight className="h-6 w-6 text-muted-foreground" />
          </button>
        </div>

        {/* Carousel indicators */}
        <div className="flex justify-center mt-4 gap-2">
          {stats.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentStatIndex(index)}
              className={`w-2 h-2 rounded-full transition-colors ${index === currentStatIndex ? 'bg-primary' : 'bg-muted-foreground/30'}`}
              aria-label={`Go to stat ${index + 1}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};