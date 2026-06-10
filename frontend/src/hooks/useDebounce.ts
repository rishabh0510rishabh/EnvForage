
// --- Advanced useDebounce Hook ---
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Configuration options for the useDebounce hook.
 */
export interface DebounceOptions {
  /** 
   * If true, the value is updated immediately on the first call, 
   * and then debounced for subsequent calls within the delay window.
   */
  leading?: boolean;
  /**
   * If true, the value is updated at the end of the delay window.
   * Default is true.
   */
  trailing?: boolean;
  /**
   * Maximum time (in ms) the value is allowed to be delayed before it's forced to update.
   */
  maxWait?: number;
}

/**
 * An advanced hook that debounces a rapidly changing value.
 * Perfect for search inputs, window resizing, or fast-firing API dependencies.
 * 
 * @param value The state value to debounce
 * @param delay The delay in milliseconds
 * @param options Configuration for leading edge and maxWait behaviors
 * @returns The debounced value, a cancel function, and a flush function
 */
export function useDebounce<T>(
  value: T,
  delay: number,
  options: DebounceOptions = {}
): [T, () => void, () => void] {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxWaitTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const isMountedRef = useRef(false);
  const lastCallTimeRef = useRef<number | null>(null);
  
  // Destructure options with defaults
  const leading = options.leading ?? false;
  const trailing = options.trailing ?? true;
  const maxWait = options.maxWait;

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (maxWaitTimeoutRef.current) {
      clearTimeout(maxWaitTimeoutRef.current);
      maxWaitTimeoutRef.current = null;
    }
    lastCallTimeRef.current = null;
  }, []);

  const flush = useCallback(() => {
    cancel();
    setDebouncedValue(value);
  }, [value, cancel]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const timeNow = Date.now();
    const isFirstCall = lastCallTimeRef.current === null;
    lastCallTimeRef.current = timeNow;

    // Handle leading edge execution
    if (isFirstCall && leading) {
      setDebouncedValue(value);
      return;
    }

    // Clear previous standard debounce timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Standard debounce timeout (trailing edge)
    if (trailing) {
      timeoutRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          setDebouncedValue(value);
          lastCallTimeRef.current = null;
          if (maxWaitTimeoutRef.current) {
            clearTimeout(maxWaitTimeoutRef.current);
            maxWaitTimeoutRef.current = null;
          }
        }
      }, delay);
    }

    // Handle maxWait forced execution
    if (maxWait !== undefined && maxWaitTimeoutRef.current === null) {
      maxWaitTimeoutRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          setDebouncedValue(value);
          // After a maxWait flush, we reset the normal debounce timeout as well
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
          maxWaitTimeoutRef.current = null;
          lastCallTimeRef.current = Date.now();
        }
      }, maxWait);
    }

    // Cleanup phase
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [value, delay, leading, trailing, maxWait]);

  return [debouncedValue, cancel, flush];
}
