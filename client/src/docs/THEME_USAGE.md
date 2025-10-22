# Centralized Theme System

This document explains how ### Theme Context

```tsx
import { useTheme } from '@/contexts/ThemeContext';

function MyComponent() {
  const { theme, actualTheme, setTheme } = useTheme();

  // theme: 'light' | 'dark' | 'system' - User's selection
  // actualTheme: 'light' | 'dark' - Resolved theme being applied
  // setTheme: (theme: 'light' | 'dark' | 'system') => void

  return (
    <div>
      <p>Selected theme: {theme}</p>
      <p>Applied theme: {actualTheme}</p>
      <button onClick={() => setTheme('dark')}>Switch to Dark</button>
    </div>
  );
}
```

### Theme Toggle Component

```tsx
import { ThemeToggle } from '@/components/ui/theme-toggle';

function SettingsPage() {
  return (
    <div>
      <h2>Appearance</h2>
      <ThemeToggle />
    </div>
  );
}
```

## How Themes Work

### Tailwind Dark Mode Integration

The theme system integrates with Tailwind's `dark:` modifier:

```tsx
// These classes automatically switch based on the theme
<div className="bg-background text-foreground dark:bg-card dark:text-card-foreground">
  Content that adapts to theme
</div>
```

### CSS Variables and Themes

CSS variables are defined for both light and dark modes:

```css
/* Light mode (default in :root) */
:root {
  --background: 0 0% 100%;    /* White background */
  --foreground: 220 13% 9%;   /* Dark text */
}

/* Dark mode overrides */
.dark {
  --background: 220 25% 12%;  /* Dark navy background */
  --foreground: 210 40% 96%; /* Light text */
}
```

### Theme Persistence

- User selections are stored in `localStorage` under the key `'theme'`
- Values: `'light'`, `'dark'`, or `'system'`
- System theme automatically updates when OS preference changes
- FOUC prevention script applies theme before React loads

## Usage Examplesalized theme system for consistent styling across the application.

## Overview

The theme system provides:
- **Centralized colors** - All brand colors in one place
- **CSS variables** - Easy to use in CSS and components
- **React hook** - Access theme in components
- **Utility functions** - Random colors, animations, etc.
- **Tailwind integration** - Brand colors available as Tailwind classes
- **Light/Dark/System themes** - User-selectable theme modes

## Theme Modes

The application supports three theme modes:

### System Theme
- Automatically follows the user's OS preference
- Switches between light and dark based on `prefers-color-scheme`
- Default mode for new users

### Light Theme
- Clean, bright interface with white backgrounds
- Dark text on light backgrounds
- Optimized for well-lit environments

### Dark Theme
- Gaming-focused dark interface
- Light text on dark backgrounds
- Default for the original design

### Theme Context

```tsx
import { useTheme } from '@/contexts/ThemeContext';

function MyComponent() {
  const { theme, actualTheme, setTheme } = useTheme();

  // theme: 'light' | 'dark' | 'system' - User's selection
  // actualTheme: 'light' | 'dark' - Resolved theme being applied
  // setTheme: (theme: 'light' | 'dark' | 'system') => void

  return (
    <div>
      <p>Selected theme: {theme}</p>
      <p>Applied theme: {actualTheme}</p>
      <button onClick={() => setTheme('dark')}>Switch to Dark</button>
    </div>
  );
}
```

### Theme Toggle Component

```tsx
import { ThemeToggle } from '@/components/ui/theme-toggle';

function SettingsPage() {
  return (
    <div>
      <h2>Appearance</h2>
      <ThemeToggle />
    </div>
  );
}
```

## Files

- `src/lib/theme.ts` - Main theme configuration
- `src/styles/theme-variables.css` - CSS variables
- `src/hooks/useTheme.ts` - React hook for theme access
- `src/contexts/ThemeContext.tsx` - Theme context and provider
- `src/components/ui/theme-toggle.tsx` - Theme toggle component
- `tailwind.config.js` - Tailwind integration

## Usage Examples

### 1. Using CSS Variables

```css
/* In your CSS files */
.my-component {
  background-color: var(--brand-teal);
  color: var(--brand-orange);
  border: 1px solid var(--brand-mint);
}

/* With opacity */
.my-overlay {
  background-color: var(--brand-teal-30);
  backdrop-filter: blur(8px);
}

/* Animation colors */
.my-glow {
  filter: drop-shadow(0 0 16px var(--logo-glow-primary));
}
```

### 2. Using Tailwind Classes

```jsx
// In your React components
<div className="bg-brand-teal text-white border-brand-orange">
  <button className="bg-brand-orange hover:bg-brand-amber">
    Click me
  </button>
</div>
```

### 3. Using the React Hook

```jsx
import { useTheme } from '@/hooks/useTheme';

function MyComponent() {
  const { colors, getRandomStarColor, getRandomAnimationDelay } = useTheme();
  
  // Access colors
  const primaryColor = colors.teal;
  
  // Get random colors for animations
  const starColor = getRandomStarColor();
  const animationDelay = getRandomAnimationDelay(1000, 5000);
  
  return (
    <div style={{ 
      backgroundColor: primaryColor,
      '--star-color': starColor,
      '--animation-delay': `${animationDelay}ms`
    }}>
      Content
    </div>
  );
}
```

### 4. Using Theme Utility Classes

```jsx
// Pre-defined utility classes
<button className="theme-btn-primary">Primary Button</button>
<button className="theme-btn-accent">Accent Button</button>
<div className="theme-bg-success theme-text-white">Success Message</div>
```

## Brand Colors

### Primary Palette
- **Teal** (`#0891B2`) - Primary brand color
- **Orange** (`#EA580C`) - Accent color
- **Mint** (`#059669`) - Success color
- **Cyan** (`#0E7490`) - Rich cyan
- **Purple** (`#7C3AED`) - Deep purple
- **Amber** (`#D97706`) - Rich amber

### Usage Guidelines
- **Teal** - Primary buttons, links, main actions
- **Orange** - Accent elements, highlights, CTAs
- **Mint** - Success states, positive feedback
- **Purple** - Special features, premium elements
- **Cyan** - Hover states for teal elements
- **Amber** - Hover states for orange elements

## Animation System

### Logo Animations
```jsx
// Logo animations use centralized colors automatically
<Logo animated={true} color="primary" />
```

### Background Animations
```jsx
// Background components can use theme colors
const { getRandomStarColor, getRandomSmokeColor } = useTheme();

// In your animation component
const starColor = getRandomStarColor();
const smokeColor = getRandomSmokeColor();
```

### Random Animation Sequences
```jsx
const { generateRandomAnimationSequence } = useTheme();

const animations = ['glow', 'pulse', 'flash', 'zoom'];
const sequence = generateRandomAnimationSequence(animations, 3);
// Returns random 3 animations without repetition
```

## Adding New Colors

### 1. Update theme.ts
```typescript
// Add to BRAND_COLORS
export const BRAND_COLORS = {
  // ... existing colors
  newColor: "#123456",
} as const;

// Add opacity variants
export const BRAND_COLORS_WITH_OPACITY = {
  // ... existing colors
  newColor: {
    10: "rgba(18, 52, 86, 0.1)",
    // ... other opacities
  },
} as const;
```

### 2. Update CSS variables
```css
/* In theme-variables.css */
:root {
  --brand-new-color: #123456;
  --brand-new-color-10: rgba(18, 52, 86, 0.1);
  /* ... other opacities */
}
```

### 3. Update Tailwind config
```javascript
// In tailwind.config.js
colors: {
  brand: {
    // ... existing colors
    newColor: "#123456",
  },
}
```

## Best Practices

1. **Always use theme colors** - Don't hardcode colors
2. **Use CSS variables** for dynamic styling
3. **Use Tailwind classes** for static styling
4. **Use the hook** for programmatic access
5. **Use utility functions** for random/dynamic colors
6. **Update all three places** when adding new colors
7. **Test animations** with the new colors
8. **Document color usage** for team consistency

## Migration Guide

### From Hardcoded Colors
```jsx
// Before
<div style={{ backgroundColor: '#0891B2' }}>

// After
<div className="bg-brand-teal">
// or
<div style={{ backgroundColor: 'var(--brand-teal)' }}>
```

### From Individual Color Definitions
```jsx
// Before
const primaryColor = '#0891B2';
const accentColor = '#EA580C';

// After
const { colors } = useTheme();
const primaryColor = colors.teal;
const accentColor = colors.orange;
```

This centralized system ensures:
- **Consistency** across the entire application
- **Easy maintenance** - change colors in one place
- **Better developer experience** - clear color naming
- **Flexible animations** - random colors without repetition
- **Type safety** - TypeScript support for all theme values
