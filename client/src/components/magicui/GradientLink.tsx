import React from "react";
import { cn } from "@/lib/utils";

interface GradientLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  children: React.ReactNode;
  href: string;
}

// Animated gradient text link with underline on hover
export const GradientLink: React.FC<GradientLinkProps> = ({ children, href, className, ...rest }) => {
  return (
    <a
      href={href}
      className={cn(
        "relative inline-flex items-center gap-1 font-medium",
        "bg-gradient-to-r from-brand-blue via-brand-cyan to-brand-mint bg-clip-text text-transparent",
        "transition-colors",
        "underline-offset-4 hover:underline",
        className
      )}
      {...rest}
    >
      {children}
    </a>
  );
};

