import React, { useState, useEffect } from 'react';


interface LogoProps {
  className?: string;
  width?: number; // optional; prefer controlling via className (e.g., w-32 h-auto)
  height?: number; // optional; prefer controlling via className (e.g., h-8 w-auto)
  variant?: 'default' | 'light' | 'dark' | 'icon-only';
  color?: 'white' | 'primary' | 'dark' | 'none'; // recolor via CSS filter for visibility
  style?: React.CSSProperties; // allow custom filters (e.g., multiple drop-shadows)
  animated?: boolean; // enable random animations
  forceColor?: boolean; // force color to always be applied, even during animations
}

export const Logo: React.FC<LogoProps> = ({
  className = '',
  width,
  height,
  variant = 'default',
  color = 'dark',
  style = {},
  animated = false,
}) => {
  const [currentAnimation, setCurrentAnimation] = useState('animate-gentleGlow');
  const [animationKey, setAnimationKey] = useState(0);
  const [lastSequence, setLastSequence] = useState<string | null>(null);

  useEffect(() => {
    if (!animated) return;

    // Sequences that complete a cycle or combine effects; 'animate-lightning' applies overlay
    // Removed slideUp, slideDown, and slideOut animations that cause logo to leave screen
    const sequences: string[][] = [
      ['animate-slowSpin animate-gentleGlow'],
      ['animate-zoomPulse', 'animate-lightning'],
      ['animate-wobble', 'animate-flash'],
      ['animate-shake', 'animate-lightning'],
      ['animate-shrinkRestore', 'animate-gentleGlow'],
    ];

    const getDuration = (cls: string) => {
      const parts = cls.split(' ');
      let d = 0;
      parts.forEach(p => {
        if (p.includes('animate-slowSpin')) d = Math.max(d, 8000);
        else if (p.includes('animate-shrinkRestore')) d = Math.max(d, 4000);
        else if (p.includes('animate-zoomPulse')) d = Math.max(d, 2800);
        else if (p.includes('animate-wobble')) d = Math.max(d, 2500);
        else if (p.includes('animate-flash')) d = Math.max(d, 1800);
        else if (p.includes('animate-shake')) d = Math.max(d, 1500);
        else if (p.includes('animate-gentleGlow')) d = Math.max(d, 3600);
        else if (p.includes('animate-lightning')) d = Math.max(d, 2200);
      });
      return d || 3000;
    };

    let timeouts: number[] = [];

    const schedule = () => {
      const delay = 5000 + Math.random() * 3000; // 5–8s
      const t = window.setTimeout(() => {
        const pool = lastSequence ? sequences.filter(s => s.join(' ') !== lastSequence) : sequences;
        const chosen = pool[Math.floor(Math.random() * pool.length)];

        let acc = 0;
        chosen.forEach((part, idx) => {
          const partDur = getDuration(part);
          const h = window.setTimeout(() => {
            setAnimationKey(prev => prev + 1);
            setCurrentAnimation(part);
          }, acc);
          timeouts.push(h);
          acc += partDur;

          // Add short pause between sequence parts
          if (idx < chosen.length - 1) {
            acc += 3000; // 3s pause between parts
          }
        });

        // Return to idle with a pause, then schedule next
        const endH = window.setTimeout(() => {
          setAnimationKey(prev => prev + 1);
          setCurrentAnimation('animate-gentleGlow');
          setLastSequence(chosen.join(' '));

          // Short still pause before next sequence
          const nextH = window.setTimeout(() => {
            schedule();
          }, 1500); // 1.5s still pause
          timeouts.push(nextH);
        }, acc);
        timeouts.push(endH);
      }, delay);
      timeouts.push(t);
    };

    schedule();
    return () => { timeouts.forEach(clearTimeout); };
  }, [animated, lastSequence]);


  const isIconOnly = variant === 'icon-only';

  // Determine theme from root element classes (AppearanceProvider sets these)
  const isLightTheme =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("light");

  // Use PNG for all non-icon variants per request
  const logoSrc = isIconOnly ? '/icon.svg' : '/logo.png';

  const logoWidth = isIconOnly ? 64 : (width ?? undefined);
  const logoHeight = isIconOnly ? 64 : (height ?? undefined);

  // Resolve color from global CSS var when not explicitly provided
  const resolvedColor = color === 'none' ? 'none' : color ?? 'dark';
  const globalPref = getComputedStyle(document.documentElement).getPropertyValue('--logo-color-scheme').trim();
  const useGlobal = color === undefined || color === 'primary' || color === 'dark' || color === 'white';
  const finalColor = useGlobal && globalPref ? (globalPref as any) : resolvedColor;

  // In light theme, keep the original multi-color art (no monochrome recolor)
  const suppressRecolorForLightTheme = isLightTheme && finalColor === 'primary';

  const colorFilter = suppressRecolorForLightTheme
    ? undefined
    : finalColor === 'white'
      ? 'brightness(0) invert(1)'
      : finalColor === 'primary'
        ? 'var(--logo-primary-filter, brightness(0) saturate(100%) invert(44%) sepia(75%) saturate(1500%) hue-rotate(180deg) brightness(90%) contrast(102%))'
        : finalColor === 'dark'
          ? 'brightness(0) saturate(100%) invert(15%) sepia(15%) saturate(1000%) hue-rotate(200deg) brightness(95%) contrast(105%)'
          : undefined;

  // Merge color filter with any existing filters, ensuring white color is preserved
  const baseFilter = colorFilter || '';
  const additionalFilter = style?.filter || '';

  // In light theme we keep the asset exactly as authored (no extra effects)
  const lightSvgEnhancement = "";

  const mergedFilter = isLightTheme
    ? (additionalFilter || '')
    : [baseFilter, additionalFilter, lightSvgEnhancement].filter(Boolean).join(' ');

  // Only add contrast aid in dark or unknown themes when not recoloring
  const needsContrastAid = !isLightTheme && !colorFilter;

  // A compact "stroke" effect using chained drop-shadows
  const contrastAid =
    "drop-shadow(0 0 0.75px rgba(0,0,0,0.35)) " +
    "drop-shadow(0 0 1.5px rgba(0,0,0,0.25)) " +
    "drop-shadow(0 1px 1px rgba(0,0,0,0.25))";

  const finalFilter = [mergedFilter, needsContrastAid ? contrastAid : ""]
    .filter(Boolean)
    .join(" ");

  const styleWithoutFilter = { ...style };
  delete styleWithoutFilter.filter;

  // Removed light-theme badge: we keep outline-only for subtle contrast without altering layout

  const wrapperClass = animated ? `relative inline-block logo-animated ${currentAnimation}` : 'relative inline-block logo-animated';
  const imgClass = `${isIconOnly ? 'rounded-lg' : ''} ${className}`.trim();

  return (
    <span className={wrapperClass} key={animated ? animationKey : undefined}>
      <img
        src={logoSrc}
        alt="Agent League Logo"
        className={imgClass}
        style={{
          maxWidth: '100%',
          height: logoHeight ? `${logoHeight}px` : undefined,
          width: logoWidth ? `${logoWidth}px` : undefined,
          objectFit: 'contain',
          ...styleWithoutFilter,
          filter: finalFilter || undefined,
        }}
      />
    </span>
  );
};

// Alternative component for when you want to use it as a link
interface LogoLinkProps extends LogoProps {
  href?: string;
  onClick?: () => void;
}

export const LogoLink: React.FC<LogoLinkProps> = ({ 
  href = '/', 
  onClick,
  ...logoProps 
}) => {
  const handleClick = (e: React.MouseEvent) => {
    if (onClick) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <a 
      href={href} 
      onClick={handleClick}
      className="inline-block transition-opacity hover:opacity-80 focus:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded"
    >
      <Logo {...logoProps} />
    </a>
  );
};
