import React from 'react';
import { useAppearance } from '@/contexts/AppearanceContext';
import { Monitor, Sun, Moon } from 'lucide-react';

interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, setTheme } = useAppearance();

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`} data-testid="theme-toggle">
      <span className="text-sm font-medium text-muted-foreground">Theme:</span>
      <div className="flex items-center space-x-1 bg-muted rounded-lg p-1">
        <button
          onClick={() => handleThemeChange('system')}
          className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            theme === 'system'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
          }`}
          data-testid="theme-option-system"
        >
          <Monitor className="h-4 w-4" />
          <span>System</span>
        </button>
        <button
          onClick={() => handleThemeChange('light')}
          className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            theme === 'light'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
          }`}
          data-testid="theme-option-light"
        >
          <Sun className="h-4 w-4" />
          <span>Light</span>
        </button>
        <button
          onClick={() => handleThemeChange('dark')}
          className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            theme === 'dark'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
          }`}
          data-testid="theme-option-dark"
        >
          <Moon className="h-4 w-4" />
          <span>Dark</span>
        </button>
      </div>
    </div>
  );
};

export default ThemeToggle;