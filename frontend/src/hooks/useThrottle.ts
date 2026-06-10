
// --- Advanced useThrottle Hook ---
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Throttle configuration options.
 */
export interface ThrottleOptions {
  /** If true, fires on the leading edge of the timeout (first call). */
  leading?: boolean;
  /** If true, fires on the trailing edge of the timeout (last call). */
  trailing?: boolean;
}

/**
 * An advanced hook that throttles a rapidly changing value.
 * Unlike debounce, which waits for a pause, throttle guarantees execution 
 * at regular intervals (e.g., executing exactly once every 100ms).
 * Highly optimized using requestAnimationFrame internally if the environment supports it.
 * 
 * @param value The value to throttle
 * @param limit The throttle interval in milliseconds
 * @param options Configuration for leading/trailing edges
 * @returns The throttled value
 */
export function useThrottle<T>(
  value: T,
  limit: number,
  options: ThrottleOptions = { leading: true, trailing: true }
): T {
  const [throttledValue, setThrottledValue] = useState<T>(value);
  const lastRan = useRef<number | null>(null);
  const trailingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rAFTimeout = useRef<number | null>(null);

  const clearTimeouts = useCallback(() => {
    if (trailingTimeout.current) {
      clearTimeout(trailingTimeout.current);
      trailingTimeout.current = null;
    }
    if (rAFTimeout.current && typeof window !== 'undefined') {
      window.cancelAnimationFrame(rAFTimeout.current);
      rAFTimeout.current = null;
    }
  }, []);

  useEffect(() => {
    return clearTimeouts;
  }, [clearTimeouts]);

  useEffect(() => {
    const timeNow = Date.now();
    const isFirstCall = lastRan.current === null;

    if (isFirstCall && options.leading === false) {
      lastRan.current = timeNow;
    }

    const runThrottledUpdate = () => {
      // Use requestAnimationFrame for smoother UI updates if in a browser environment
      if (typeof window !== 'undefined' && window.requestAnimationFrame) {
        if (rAFTimeout.current) window.cancelAnimationFrame(rAFTimeout.current);
        rAFTimeout.current = window.requestAnimationFrame(() => {
          setThrottledValue(value);
          lastRan.current = Date.now();
        });
      } else {
        setThrottledValue(value);
        lastRan.current = Date.now();
      }
    };

    if (lastRan.current === null || timeNow - lastRan.current >= limit) {
      // It's been long enough since the last run, fire immediately
      if (trailingTimeout.current) {
        clearTimeout(trailingTimeout.current);
        trailingTimeout.current = null;
      }
      runThrottledUpdate();
    } else if (options.trailing) {
      // It hasn't been long enough, but we want to catch the trailing edge
      if (trailingTimeout.current) {
        clearTimeout(trailingTimeout.current);
      }
      trailingTimeout.current = setTimeout(() => {
        // If leading is false, we want to reset the lastRan timestamp entirely 
        // to prevent immediate firing on the next fast cycle.
        lastRan.current = options.leading === false ? null : Date.now();
        runThrottledUpdate();
      }, limit - (timeNow - lastRan.current));
    }
    
  }, [value, limit, options.leading, options.trailing]);

  return throttledValue;
}
