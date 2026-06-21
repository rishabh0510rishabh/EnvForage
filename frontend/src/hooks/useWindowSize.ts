
// --- Advanced useWindowSize Hook ---
import { useState, useEffect, useCallback } from 'react';

export interface WindowSize {
  width: number;
  height: number;
  isLandscape: boolean;
  isPortrait: boolean;
  dpr: number; // Device Pixel Ratio (e.g., Retina screens)
}

/**
 * An advanced, highly optimized hook that tracks the window dimensions.
 * Avoids the classic Next.js SSR "Text content did not match" hydration error 
 * by forcing the initial render to match the server (width 0), then updating immediately.
 * Throttles the resize listener to prevent React re-render thrashing.
 */
export function useWindowSize(): WindowSize {
  // Initialize with safe 0s for SSR compliance
  const [size, setSize] = useState<WindowSize>({
    width: 0,
    height: 0,
    isLandscape: true,
    isPortrait: false,
    dpr: 1,
  });

  const [isMounted, setIsMounted] = useState(false);

  // Throttled setter logic
  const handleResize = useCallback(() => {
    // requestAnimationFrame ensures we only calculate layout when the browser is ready to paint
    window.requestAnimationFrame(() => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      setSize({
        width,
        height,
        isLandscape: width >= height,
        isPortrait: height > width,
        dpr: window.devicePixelRatio || 1,
      });
    });
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsMounted(true);
    // Set the actual size immediately once mounted on the client
    handleResize();
    
    // Add event listeners
    window.addEventListener('resize', handleResize, { passive: true });
    
    // iOS/Android specific orientation change listener
    // This is sometimes faster and more reliable on mobile than the standard resize event
    window.addEventListener('orientationchange', () => {
      // Orientation changes take a few ms to propagate new dimensions
      setTimeout(handleResize, 100); 
    });

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, [handleResize]);

  // If we haven't mounted yet, we return the 0-state.
  // We can optionally use a heuristic here (e.g. assume 1024x768 for SSR layout)
  // but returning 0 forces developers to write defensive CSS that scales up gracefully.
  if (!isMounted) {
    return { width: 0, height: 0, isLandscape: true, isPortrait: false, dpr: 1 };
  }

  return size;
}

/**
 * Derivative hook focusing purely on scroll position with similar performance optimizations.
 */
export function useWindowScroll() {
  const [scroll, setScroll] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleScroll = () => {
      window.requestAnimationFrame(() => {
        setScroll({
          x: window.scrollX,
          y: window.scrollY
        });
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return scroll;
}
