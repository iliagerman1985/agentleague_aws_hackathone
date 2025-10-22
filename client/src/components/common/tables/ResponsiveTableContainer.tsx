import React, { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface ResponsiveTableContainerProps {
  children: React.ReactNode;
  className?: string;
  minWidth?: number;
}

export const ResponsiveTableContainer: React.FC<ResponsiveTableContainerProps> = ({
  children,
  className,
  minWidth = 560,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [canScroll, setCanScroll] = useState(false);
  const [atEnd, setAtEnd] = useState(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) {
      return;
    }

    const update = () => {
      const hasOverflow = Math.ceil(el.scrollWidth - el.clientWidth) > 4;
      setCanScroll(hasOverflow);
      setAtEnd(!hasOverflow || el.scrollLeft >= el.scrollWidth - el.clientWidth - 4);
    };

    const handleScroll = () => {
      setAtEnd(el.scrollLeft >= el.scrollWidth - el.clientWidth - 4);
    };

    update();
    el.addEventListener("scroll", handleScroll, { passive: true });

    const resizeObserver = new ResizeObserver(update);
    resizeObserver.observe(el);

    return () => {
      el.removeEventListener("scroll", handleScroll);
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <div className={cn("relative overflow-hidden rounded-xl border bg-card", className)}>
      <div ref={scrollRef} className="w-full overflow-x-auto pb-1">
        <div style={{ minWidth }} className="min-w-full sm:min-w-0">
          {children}
        </div>
      </div>
      {canScroll && !atEnd && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-card via-card/70 to-transparent transition-opacity duration-200 sm:hidden"
        />
      )}
    </div>
  );
};

export default ResponsiveTableContainer;
