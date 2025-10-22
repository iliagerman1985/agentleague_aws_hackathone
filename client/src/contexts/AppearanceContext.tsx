import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'system';

export type ColorScheme = 'red-blue' | 'purple-cyan' | 'emerald-amber' | 'indigo-rose' | 'teal-orange' | 'violet-lime';

export interface ColorSchemeOption {
  id: ColorScheme;
  name: string;
  description: string;
  primary: string;
  accent: string;
  preview: {
    primary: string;
    accent: string;
    background: string;
  };
}

export const COLOR_SCHEMES: ColorSchemeOption[] = [
  {
    id: 'red-blue',
    name: 'Classic Gaming',
    description: 'Teal primary with warm orange accent',
    primary: '#0891B2',
    accent: '#EA580C',
    preview: { primary: '#0891B2', accent: '#EA580C', background: '#1A2B2B' }
  },
  {
    id: 'purple-cyan',
    name: 'Futuristic Tech',
    description: 'Modern purple and cyan',
    primary: '#7C3AED',
    accent: '#06B6D4',
    preview: { primary: '#7C3AED', accent: '#06B6D4', background: '#1A1B3C' }
  },
  {
    id: 'emerald-amber',
    name: 'Natural Energy',
    description: 'Fresh emerald and amber',
    primary: '#10B981',
    accent: '#F59E0B',
    preview: { primary: '#10B981', accent: '#F59E0B', background: '#1A2E1A' }
  },
  {
    id: 'indigo-rose',
    name: 'Premium Gaming',
    description: 'Sophisticated indigo and rose',
    primary: '#4F46E5',
    accent: '#F43F5E',
    preview: { primary: '#4F46E5', accent: '#F43F5E', background: '#1A1A3A' }
  },
  {
    id: 'teal-orange',
    name: 'Balanced Contrast',
    description: 'High contrast teal and orange',
    primary: '#0891B2',
    accent: '#EA580C',
    preview: { primary: '#0891B2', accent: '#EA580C', background: '#1A2B2B' }
  },
  {
    id: 'violet-lime',
    name: 'Bold & Modern',
    description: 'Eye-catching violet and lime',
    primary: '#8B5CF6',
    accent: '#84CC16',
    preview: { primary: '#8B5CF6', accent: '#84CC16', background: '#2A1A3A' }
  }
];

const LOGO_FILTERS: Record<ColorScheme, string> = {
  'red-blue': 'brightness(0) saturate(100%) invert(51%) sepia(89%) saturate(1178%) hue-rotate(161deg) brightness(94%) contrast(95%)',
  'purple-cyan': 'brightness(0) saturate(100%) invert(22%) sepia(84%) saturate(5930%) hue-rotate(264deg) brightness(96%) contrast(102%)',
  'emerald-amber': 'brightness(0) saturate(100%) invert(58%) sepia(69%) saturate(1817%) hue-rotate(120deg) brightness(91%) contrast(86%)',
  'indigo-rose': 'brightness(0) saturate(100%) invert(29%) sepia(99%) saturate(1678%) hue-rotate(234deg) brightness(95%) contrast(94%)',
  'teal-orange': 'brightness(0) saturate(100%) invert(51%) sepia(89%) saturate(1178%) hue-rotate(161deg) brightness(94%) contrast(95%)',
  'violet-lime': 'brightness(0) saturate(100%) invert(43%) sepia(50%) saturate(2878%) hue-rotate(246deg) brightness(95%) contrast(95%)'
};


interface AppearanceContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  actualTheme: 'light' | 'dark';
  backgroundAnimations: boolean;
  setBackgroundAnimations: (value: boolean) => void;
  colorScheme: ColorScheme;
  setColorScheme: (scheme: ColorScheme) => void;
}

const AppearanceContext = createContext<AppearanceContextType | undefined>(undefined);

export const useAppearance = () => {
  const context = useContext(AppearanceContext);
  if (context === undefined) {
    throw new Error('useAppearance must be used within an AppearanceProvider');
  }
  return context;
};

interface AppearanceProviderProps {
  children: ReactNode;
}

export const AppearanceProvider: React.FC<AppearanceProviderProps> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>('system');
  const [actualTheme, setActualTheme] = useState<'light' | 'dark'>('dark');
  const [backgroundAnimations, setBackgroundAnimationsState] = useState(true);
  const [colorScheme, setColorSchemeState] = useState<ColorScheme>('teal-orange');

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as Theme | null;
    const initialTheme: Theme = savedTheme && ['light', 'dark', 'system'].includes(savedTheme) ? savedTheme : 'dark';
    setThemeState(initialTheme);

    const savedAnimations = localStorage.getItem('backgroundAnimations');
    if (savedAnimations !== null) {
      setBackgroundAnimationsState(JSON.parse(savedAnimations));
    }

    const savedColorScheme = localStorage.getItem('colorScheme') as ColorScheme | null;
    const initialColorScheme: ColorScheme = savedColorScheme && COLOR_SCHEMES.some(cs => cs.id === savedColorScheme)
      ? savedColorScheme
      : 'teal-orange';
    setColorSchemeState(initialColorScheme);
  }, []);

  const getSystemTheme = (): 'light' | 'dark' => {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  const resolveActualTheme = (userTheme: Theme): 'light' | 'dark' => {
    return userTheme === 'system' ? getSystemTheme() : userTheme;
  };

  const applyTheme = (resolvedTheme: 'light' | 'dark') => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);
    setActualTheme(resolvedTheme);
  };

  const hexToHsl = (hex: string): string => {
    // Convert hex to RGB
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0;
    let s = 0;
    const l = (max + min) / 2;

    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h /= 6;
    }

    return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
  };

  const applyColorScheme = (scheme: ColorScheme) => {
    const root = document.documentElement;
    const schemeData = COLOR_SCHEMES.find(cs => cs.id === scheme);
    if (schemeData) {
      // Set hex values for theme-variables.css
      root.style.setProperty('--color-scheme-primary', schemeData.primary);
      root.style.setProperty('--color-scheme-accent', schemeData.accent);

      // Convert to HSL for index.css variables
      const primaryHsl = hexToHsl(schemeData.primary);
      const accentHsl = hexToHsl(schemeData.accent);

      // Update HSL variables used by shadcn components
      root.style.setProperty('--primary', primaryHsl);
      root.style.setProperty('--ring', primaryHsl);
      root.style.setProperty('--accent', accentHsl);
      root.style.setProperty('--button-primary', primaryHsl);

      // Update logo filter to match the primary color
      const logoFilter = LOGO_FILTERS[scheme];
      root.style.setProperty('--logo-primary-filter', logoFilter);

      root.setAttribute('data-color-scheme', scheme);
    }
  };

  useEffect(() => {
    applyColorScheme(colorScheme);
  }, [colorScheme]);

  useEffect(() => {
    const resolvedTheme = resolveActualTheme(theme);
    applyTheme(resolvedTheme);

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => applyTheme(getSystemTheme());
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const setBackgroundAnimations = (value: boolean) => {
    setBackgroundAnimationsState(value);
    localStorage.setItem('backgroundAnimations', JSON.stringify(value));
  };

  const setColorScheme = (scheme: ColorScheme) => {
    setColorSchemeState(scheme);
    localStorage.setItem('colorScheme', scheme);
  };

  const value: AppearanceContextType = {
    theme,
    setTheme,
    actualTheme,
    backgroundAnimations,
    setBackgroundAnimations,
    colorScheme,
    setColorScheme,
  };

  return (
    <AppearanceContext.Provider value={value}>
      {children}
    </AppearanceContext.Provider>
  );
};
