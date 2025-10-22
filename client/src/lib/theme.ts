/**
 * Centralized Theme Configuration
 * All colors, animations, and styling constants in one place
 */

// Brand Colors - Primary palette
export const BRAND_COLORS = {
  // Primary colors
  primaryRed: "#E53E3E",  // Primary red for buttons and key actions
  teal: "#38B2AC",        // Teal accent color
  orange: "#E53E3E",      // Map to primary red for compatibility
  mint: "#48BB78",        // Success/mint color
  cyan: "#38B2AC",        // Rich cyan (same as teal)
  purple: "#805AD5",      // Deep purple
  amber: "#ED8936",       // Rich amber
  
  // Neutral colors
  slate: "#475569",       // Rich slate gray for text
  lightBlue: "#E0F2FE",   // Very light blue for backgrounds
  warmGray: "#F5F5F4",    // Warm light gray
  
  // Semantic colors
  success: "#48BB78",     // Same as mint
  warning: "#ED8936",     // Same as amber
  error: "#DC2626",       // Red for errors
  info: "#38B2AC",        // Same as teal
} as const;

// Color variations with opacity
export const BRAND_COLORS_WITH_OPACITY = {
  primaryRed: {
    10: "rgba(229, 62, 62, 0.1)",
    20: "rgba(229, 62, 62, 0.2)",
    30: "rgba(229, 62, 62, 0.3)",
    40: "rgba(229, 62, 62, 0.4)",
    50: "rgba(229, 62, 62, 0.5)",
    60: "rgba(229, 62, 62, 0.6)",
    70: "rgba(229, 62, 62, 0.7)",
    80: "rgba(229, 62, 62, 0.8)",
    90: "rgba(229, 62, 62, 0.9)",
    100: "rgba(229, 62, 62, 1)",
  },
  teal: {
    10: "rgba(56, 178, 172, 0.1)",
    20: "rgba(56, 178, 172, 0.2)",
    30: "rgba(56, 178, 172, 0.3)",
    40: "rgba(56, 178, 172, 0.4)",
    50: "rgba(56, 178, 172, 0.5)",
    60: "rgba(56, 178, 172, 0.6)",
    70: "rgba(56, 178, 172, 0.7)",
    80: "rgba(56, 178, 172, 0.8)",
    90: "rgba(56, 178, 172, 0.9)",
    100: "rgba(56, 178, 172, 1)",
  },
  orange: {
    10: "rgba(229, 62, 62, 0.1)",
    20: "rgba(229, 62, 62, 0.2)",
    30: "rgba(229, 62, 62, 0.3)",
    40: "rgba(229, 62, 62, 0.4)",
    50: "rgba(229, 62, 62, 0.5)",
    60: "rgba(229, 62, 62, 0.6)",
    70: "rgba(229, 62, 62, 0.7)",
    80: "rgba(229, 62, 62, 0.8)",
    90: "rgba(229, 62, 62, 0.9)",
    100: "rgba(229, 62, 62, 1)",
  },
  mint: {
    10: "rgba(72, 187, 120, 0.1)",
    20: "rgba(72, 187, 120, 0.2)",
    30: "rgba(72, 187, 120, 0.3)",
    40: "rgba(72, 187, 120, 0.4)",
    50: "rgba(72, 187, 120, 0.5)",
    60: "rgba(72, 187, 120, 0.6)",
    70: "rgba(72, 187, 120, 0.7)",
    80: "rgba(72, 187, 120, 0.8)",
    90: "rgba(72, 187, 120, 0.9)",
    100: "rgba(72, 187, 120, 1)",
  },
  purple: {
    10: "rgba(124, 58, 237, 0.1)",
    20: "rgba(124, 58, 237, 0.2)",
    30: "rgba(124, 58, 237, 0.3)",
    40: "rgba(124, 58, 237, 0.4)",
    50: "rgba(124, 58, 237, 0.5)",
    60: "rgba(124, 58, 237, 0.6)",
    70: "rgba(124, 58, 237, 0.7)",
    80: "rgba(124, 58, 237, 0.8)",
    90: "rgba(124, 58, 237, 0.9)",
    100: "rgba(124, 58, 237, 1)",
  },
  cyan: {
    10: "rgba(56, 178, 172, 0.1)",
    20: "rgba(56, 178, 172, 0.2)",
    30: "rgba(56, 178, 172, 0.3)",
    40: "rgba(56, 178, 172, 0.4)",
    50: "rgba(56, 178, 172, 0.5)",
    60: "rgba(56, 178, 172, 0.6)",
    70: "rgba(56, 178, 172, 0.7)",
    80: "rgba(56, 178, 172, 0.8)",
    90: "rgba(56, 178, 172, 0.9)",
    100: "rgba(56, 178, 172, 1)",
  },
  amber: {
    10: "rgba(237, 137, 54, 0.1)",
    20: "rgba(237, 137, 54, 0.2)",
    30: "rgba(237, 137, 54, 0.3)",
    40: "rgba(237, 137, 54, 0.4)",
    50: "rgba(237, 137, 54, 0.5)",
    60: "rgba(237, 137, 54, 0.6)",
    70: "rgba(237, 137, 54, 0.7)",
    80: "rgba(237, 137, 54, 0.8)",
    90: "rgba(237, 137, 54, 0.9)",
    100: "rgba(237, 137, 54, 1)",
  },
} as const;

// Animation configurations
export const ANIMATION_CONFIG = {
  // Logo animations
  logo: {
    glowColors: [BRAND_COLORS_WITH_OPACITY.teal[60], BRAND_COLORS_WITH_OPACITY.amber[40]],
    flashColors: [BRAND_COLORS_WITH_OPACITY.amber[80], BRAND_COLORS_WITH_OPACITY.teal[60], BRAND_COLORS_WITH_OPACITY.purple[40]],
    pulseColors: [BRAND_COLORS_WITH_OPACITY.teal[70], BRAND_COLORS_WITH_OPACITY.amber[60], BRAND_COLORS_WITH_OPACITY.mint[40]],
    lightningGradient: `linear-gradient(120deg, ${BRAND_COLORS_WITH_OPACITY.amber[10]} 0%, ${BRAND_COLORS_WITH_OPACITY.amber[80]} 25%, ${BRAND_COLORS_WITH_OPACITY.teal[60]} 45%, ${BRAND_COLORS_WITH_OPACITY.purple[40]} 50%, ${BRAND_COLORS_WITH_OPACITY.mint[30]} 65%, ${BRAND_COLORS_WITH_OPACITY.amber[10]} 100%)`,
  },
  
  // Background animations
  background: {
    starColors: [
      BRAND_COLORS_WITH_OPACITY.primaryRed[70],
      BRAND_COLORS_WITH_OPACITY.teal[60],
      BRAND_COLORS_WITH_OPACITY.mint[50],
      BRAND_COLORS_WITH_OPACITY.purple[40],
      BRAND_COLORS_WITH_OPACITY.cyan[60],
      BRAND_COLORS_WITH_OPACITY.amber[50],
    ],
    smokeColors: [
      BRAND_COLORS_WITH_OPACITY.primaryRed[30],
      BRAND_COLORS_WITH_OPACITY.teal[20],
      BRAND_COLORS_WITH_OPACITY.mint[20],
      BRAND_COLORS_WITH_OPACITY.purple[20],
      BRAND_COLORS_WITH_OPACITY.cyan[20],
      BRAND_COLORS_WITH_OPACITY.amber[20],
    ],
  },
  
  // Timing configurations
  timing: {
    logoAnimationInterval: [3000, 6000], // Random between 3-6 seconds
    backgroundStarInterval: [2000, 5000], // Random between 2-5 seconds
    backgroundSmokeInterval: [4000, 8000], // Random between 4-8 seconds
  },
} as const;

// CSS class mappings for easy use
export const THEME_CLASSES = {
  // Background colors
  bg: {
    primary: "bg-brand-primaryTeal",
    accent: "bg-brand-accentOrange",
    success: "bg-brand-mint",
    muted: "bg-slate-100",
    card: "bg-white",
  },

  // Text colors
  text: {
    primary: "text-brand-primaryTeal",
    accent: "text-brand-accentOrange",
    success: "text-brand-mint",
    muted: "text-slate-600",
    dark: "text-slate-800",
  },

  // Border colors
  border: {
    primary: "border-brand-primaryTeal",
    accent: "border-brand-accentOrange",
    success: "border-brand-mint",
    muted: "border-slate-200",
  },

  // Button variants
  button: {
    primary: "bg-brand-primaryTeal hover:bg-brand-accentOrange text-white",
    accent: "bg-brand-accentOrange hover:bg-brand-primaryTeal text-white",
    success: "bg-brand-mint hover:bg-emerald-600 text-white",
    outline: "border-brand-primaryTeal text-brand-primaryTeal hover:bg-brand-primaryTeal hover:text-white",
  },
} as const;

// Utility functions for random color selection
export const getRandomColor = (colorArray: readonly string[]) => {
  return colorArray[Math.floor(Math.random() * colorArray.length)];
};

export const getRandomAnimationDelay = (min: number, max: number) => {
  return Math.floor(Math.random() * (max - min + 1)) + min;
};

// Generate random animation sequences to prevent repetition
export const generateRandomAnimationSequence = (animations: string[], count: number = 3) => {
  const sequence: string[] = [];
  const available = [...animations];
  
  for (let i = 0; i < count && available.length > 0; i++) {
    const randomIndex = Math.floor(Math.random() * available.length);
    sequence.push(available.splice(randomIndex, 1)[0]);
  }
  
  return sequence;
};

// Export default theme object
export const THEME = {
  colors: BRAND_COLORS,
  colorsWithOpacity: BRAND_COLORS_WITH_OPACITY,
  animation: ANIMATION_CONFIG,
  classes: THEME_CLASSES,
  utils: {
    getRandomColor,
    getRandomAnimationDelay,
    generateRandomAnimationSequence,
  },
} as const;

export default THEME;
