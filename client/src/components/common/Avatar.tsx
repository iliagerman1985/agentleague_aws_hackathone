import React from "react";
import { cn } from "@/lib/utils";

export interface AvatarProps {
  /** Avatar source URL or base64 data URL */
  src?: string | null;
  /** Fallback text to display when no image (typically initials) */
  fallback?: string;
  /** Size of the avatar */
  size?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl" | "5xl";
  /** Custom CSS classes */
  className?: string;
  /** Alt text for accessibility */
  alt?: string;
  /** Whether to show a border */
  showBorder?: boolean;
  /** Avatar type for styling different sources */
  type?: "default" | "google" | "uploaded";
}

const sizeClasses = {
  sm: "h-6 w-6 text-xs",
  md: "h-8 w-8 text-sm",
  lg: "h-10 w-10 text-base",
  xl: "h-12 w-12 text-lg",
  "2xl": "h-16 w-16 text-xl",
  "3xl": "h-20 w-20 text-2xl",
  "4xl": "h-24 w-24 text-3xl",
  "5xl": "h-28 w-28 text-4xl",
};

const fallbackSizeClasses = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-base",
  xl: "text-lg",
  "2xl": "text-xl",
  "3xl": "text-2xl",
  "4xl": "text-3xl",
  "5xl": "text-4xl",
};

/**
 * Avatar component for displaying user/agent profile images with fallbacks.
 * Supports automatic initials generation and different avatar sources.
 */
export const Avatar: React.FC<AvatarProps> = ({
  src,
  fallback,
  size = "md",
  className,
  alt = "Avatar",
  showBorder = true,
  type = "default",
}) => {
  const [imageError, setImageError] = React.useState(false);
  const [imageLoaded, setImageLoaded] = React.useState(false);

  const timeoutRef = React.useRef<number | null>(null);

  // Reset state when src changes and set a timeout to fall back if load stalls
  React.useEffect(() => {
    setImageError(false);
    setImageLoaded(false);
    // clear any existing timeout
    if (timeoutRef.current) window.clearTimeout(timeoutRef.current);

    // Only use timeout for external URLs (http/https)
    // Local paths (/avatars/...) and data URLs load quickly and don't need timeouts
    if (src && src.startsWith('http')) {
      timeoutRef.current = window.setTimeout(() => {
        console.warn('[Avatar] Image load timeout:', { src: src.substring(0, 100), fallback });
        setImageError(true);
      }, 5000); // Increased to 5 seconds for external URLs
    }
    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    };
  }, [src, fallback]);

  // Generate fallback text from provided fallback or extract initials
  const getFallbackText = () => {
    if (fallback) {
      // Extract initials from fallback text
      return fallback
        .split(" ")
        .map(word => word.charAt(0).toUpperCase())
        .slice(0, 2)
        .join("");
    }
    return "?";
  };

  // Generate background color based on fallback text for consistency
  const getBackgroundColor = () => {
    if (!fallback) return "bg-gray-400";

    // Simple hash-based color generation
    let hash = 0;
    for (let i = 0; i < fallback.length; i++) {
      hash = fallback.charCodeAt(i) + ((hash << 5) - hash);
    }

    const colors = [
      "bg-red-500",
      "bg-blue-500",
      "bg-green-500",
      "bg-yellow-500",
      "bg-purple-500",
      "bg-pink-500",
      "bg-indigo-500",
      "bg-teal-500",
      "bg-orange-500",
      "bg-cyan-500",
    ];

    return colors[Math.abs(hash) % colors.length];
  };

  const handleImageError = () => {
    if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    const srcPreview = src ? (src.startsWith('data:') ? `data:${src.substring(5, 50)}...` : src) : 'null';
    console.warn('[Avatar] Image failed to load:', { src: srcPreview, fallback, type });
    setImageError(true);
  };

  const handleImageLoad = () => {
    if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    const srcPreview = src ? (src.startsWith('data:') ? `data:${src.substring(5, 50)}...` : src) : 'null';
    console.log('[Avatar] Image loaded successfully:', { src: srcPreview, fallback, type });
    setImageError(false);
    setImageLoaded(true);
  };

  // Show fallback if no src or if image failed to load
  const shouldShowFallback = !src || imageError;

  return (
    <div
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-medium text-white transition-colors",
        sizeClasses[size],
        showBorder && "ring-2 ring-white ring-offset-2 ring-offset-gray-100",
        shouldShowFallback && getBackgroundColor(),
        !shouldShowFallback && !imageLoaded && "bg-gray-200",
        className
      )}
    >
      {shouldShowFallback ? (
        <span className={cn("font-semibold", fallbackSizeClasses[size])}>
          {getFallbackText()}
        </span>
      ) : (
        <img
          ref={(imgElement) => {
            if (imgElement && imgElement.complete && !imageLoaded && !imageError) {
              setImageLoaded(true);
            }
          }}
          src={src || undefined}
          alt={alt}
          loading="eager"
          decoding="async"
          className={cn(
            "h-full w-full object-cover",
            !imageLoaded && "opacity-0"
          )}
          onError={handleImageError}
          onLoad={handleImageLoad}
        />
      )}

      {/* Optional indicator for different avatar types */}
      {type === "google" && (
        <div className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-blue-500 ring-2 ring-white" title="Google Profile" />
      )}
    </div>
  );
};

export default Avatar;