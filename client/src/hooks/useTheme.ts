import { THEME } from '@/lib/theme';

/**
 * Hook to access centralized theme configuration
 * Provides easy access to colors, animations, and utility functions
 */
export const useTheme = () => {
  return {
    // Direct access to theme object
    theme: THEME,
    
    // Convenience accessors
    colors: THEME.colors,
    colorsWithOpacity: THEME.colorsWithOpacity,
    animation: THEME.animation,
    classes: THEME.classes,
    
    // Utility functions
    getRandomColor: THEME.utils.getRandomColor,
    getRandomAnimationDelay: THEME.utils.getRandomAnimationDelay,
    generateRandomAnimationSequence: THEME.utils.generateRandomAnimationSequence,
    
    // Helper functions for common use cases
    getRandomStarColor: () => THEME.utils.getRandomColor(THEME.animation.background.starColors),
    getRandomSmokeColor: () => THEME.utils.getRandomColor(THEME.animation.background.smokeColors),
    getRandomLogoAnimationDelay: () => THEME.utils.getRandomAnimationDelay(
      THEME.animation.timing.logoAnimationInterval[0],
      THEME.animation.timing.logoAnimationInterval[1]
    ),
    getRandomBackgroundStarDelay: () => THEME.utils.getRandomAnimationDelay(
      THEME.animation.timing.backgroundStarInterval[0],
      THEME.animation.timing.backgroundStarInterval[1]
    ),
    getRandomBackgroundSmokeDelay: () => THEME.utils.getRandomAnimationDelay(
      THEME.animation.timing.backgroundSmokeInterval[0],
      THEME.animation.timing.backgroundSmokeInterval[1]
    ),
  };
};

export default useTheme;
