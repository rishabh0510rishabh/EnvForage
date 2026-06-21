
// --- Advanced useMediaQuery Hook ---
import { useState, useEffect, useCallback } from 'react';

/**
 * A highly robust, SSR-safe hook that tracks CSS media queries programmatically.
 * Utilizes the modern matchMedia API and handles the deprecated addListener gracefully.
 * 
 * Usage:
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * const isDark = useMediaQuery('(prefers-color-scheme: dark)');
 * 
 * @param query The CSS media query string (e.g. '(min-width: 1024px)')
 * @param defaultValue The default boolean value to return during Server-Side Rendering (SSR)
 * @returns boolean indicating if the query currently matches
 */
export function useMediaQuery(query: string, defaultValue: boolean = false): boolean {
  // State initialization function. We avoid doing window.matchMedia immediately 
  // on init to prevent Hydration mismatches between Server and Client in Next.js.
  const [matches, setMatches] = useState<boolean>(defaultValue);
  
  // Track if hydration has completed
  const [isHydrated, setIsHydrated] = useState(false);

  // We set the initial accurate state only after the component has mounted
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsHydrated(true);
    if (typeof window !== 'undefined' && window.matchMedia) {
      const media = window.matchMedia(query);
      if (media.matches !== matches) {
        setMatches(media.matches);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const handleChange = useCallback((event: MediaQueryListEvent) => {
    setMatches(event.matches);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) {
      return undefined;
    }

    const mediaQueryList = window.matchMedia(query);

    // Some older browsers don't support addEventListener on MediaQueryList
    if (mediaQueryList.addEventListener) {
      mediaQueryList.addEventListener('change', handleChange);
      return () => {
        mediaQueryList.removeEventListener('change', handleChange);
      };
    } else if (mediaQueryList.addListener) {
      // Deprecated fallback for older WebKit / IE
      mediaQueryList.addListener(handleChange);
      return () => {
        mediaQueryList.removeListener(handleChange);
      };
    }
  }, [query, handleChange]);

  // Before hydration, we return the SSR default to prevent React hydration errors
  if (!isHydrated) {
    return defaultValue;
  }

  return matches;
}

/**
 * Pre-defined responsive breakpoint hooks matching standard Tailwind sizes.
 */
export const useIsMobile = () => useMediaQuery('(max-width: 639px)');
export const useIsTablet = () => useMediaQuery('(min-width: 640px) and (max-width: 1023px)');
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)');
export const usePrefersDarkMode = () => useMediaQuery('(prefers-color-scheme: dark)', true);
export const usePrefersReducedMotion = () => useMediaQuery('(prefers-reduced-motion: reduce)');
