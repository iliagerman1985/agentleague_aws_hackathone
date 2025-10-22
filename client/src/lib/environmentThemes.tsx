/**
 * Environment-specific theming system
 * Maps game environments to colors, icons, and visual styles
 */

import React from "react";
import { Crown, Spade, Gamepad2 } from "lucide-react";

export type EnvironmentType = "chess" | "texas_holdem" | "generic";

export interface EnvironmentTheme {
  id: EnvironmentType;
  name: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
  };
  gradients: {
    card: string;
    background: string;
  };
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string; // Tailwind color class for the icon
}

export const ENVIRONMENT_THEMES: Record<EnvironmentType, EnvironmentTheme> = {
  chess: {
    id: "chess",
    name: "Chess",
    colors: {
      primary: "#8B7355", // Warm brown (chess board)
      secondary: "#F0D9B5", // Light square
      accent: "#B58863", // Dark square
      background: "#2C2416", // Deep brown
    },
    gradients: {
      card: "from-slate-800/12 via-slate-700/6 to-transparent",
      background: "from-slate-900/16 via-transparent to-transparent",
    },
    icon: Crown,
    iconColor: "text-yellow-500",
  },
  texas_holdem: {
    id: "texas_holdem",
    name: "Texas Hold'em",
    colors: {
      primary: "#DC2626", // Card red
      secondary: "#059669", // Felt green
      accent: "#1F2937", // Card black
      background: "#0F172A", // Deep blue-black
    },
    gradients: {
      card: "from-emerald-900/20 via-emerald-700/10 to-transparent",
      background: "from-emerald-950/25 via-transparent to-transparent",
    },
    icon: Spade,
    iconColor: "text-red-500",
  },
  generic: {
    id: "generic",
    name: "Generic",
    colors: {
      primary: "hsl(var(--primary))",
      secondary: "hsl(var(--secondary))",
      accent: "hsl(var(--accent))",
      background: "hsl(var(--background))",
    },
    gradients: {
      card: "from-primary/10 via-primary/5 to-transparent",
      background: "from-primary/5 via-transparent to-transparent",
    },
    icon: Gamepad2,
    iconColor: "text-purple-500",
  },
};

/**
 * Get theme for a specific environment
 */
export function getEnvironmentTheme(env: string | undefined): EnvironmentTheme {
  if (!env) return ENVIRONMENT_THEMES.generic;
  
  const normalized = env.toLowerCase() as EnvironmentType;
  return ENVIRONMENT_THEMES[normalized] || ENVIRONMENT_THEMES.generic;
}

/**
 * Get CSS variables for an environment theme
 */
export function getEnvironmentCSSVars(env: string | undefined): Record<string, string> {
  const theme = getEnvironmentTheme(env);
  return {
    "--env-primary": theme.colors.primary,
    "--env-secondary": theme.colors.secondary,
    "--env-accent": theme.colors.accent,
    "--env-background": theme.colors.background,
  };
}

