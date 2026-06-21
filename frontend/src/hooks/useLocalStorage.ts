
// --- Advanced useLocalStorage Hook ---
import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Configuration options for the local storage hook.
 */
export interface LocalStorageOptions<T> {
  /** Optional custom serializer. Defaults to JSON.stringify */
  serializer?: (value: T) => string;
  /** Optional custom deserializer. Defaults to JSON.parse */
  deserializer?: (value: string) => T;
  /** If true, synchronizes state changes across multiple browser tabs */
  syncCrossTab?: boolean;
}

// Global Event target used to sync hooks within the SAME tab
const localStorageEventTarget = typeof window !== 'undefined' ? new EventTarget() : null;

/**
 * A highly robust `useLocalStorage` hook.
 * Handles Next.js SSR hydration, complex generic object serialization, 
 * in-tab component syncing, and cross-tab Window storage events.
 * 
 * @param key The localStorage key
 * @param initialValue The default value if not found
 * @param options Configuration options
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T | (() => T),
  options: LocalStorageOptions<T> = {}
): [T, (value: T | ((val: T) => T)) => void, () => void] {
  
  const {
    serializer = JSON.stringify,
    deserializer = JSON.parse,
    syncCrossTab = true,
  } = options;

  // Initialize state lazily to avoid heavy parsing on every render
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? deserializer(item) : (typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue);
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue;
    }
  });

  // Keep a ref to the latest value to avoid stale closures in event listeners.
  // The assignment is done in an effect to satisfy the react-hooks/refs lint rule.
  const valueRef = useRef(storedValue);
  useEffect(() => {
    valueRef.current = storedValue;
  });

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(valueRef.current) : value;
        setStoredValue(valueToStore);
        
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, serializer(valueToStore));
          // Dispatch a custom event so other identical hooks in the *same* tab update
          localStorageEventTarget?.dispatchEvent(
            new CustomEvent('local-storage', { detail: { key, newValue: valueToStore } })
          );
        }
      } catch (error) {
        console.warn(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, serializer]
  );

  const removeValue = useCallback(() => {
    try {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(key);
        localStorageEventTarget?.dispatchEvent(
          new CustomEvent('local-storage', { detail: { key, newValue: undefined } })
        );
      }
      setStoredValue(typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue);
    } catch (error) {
      console.warn(`Error removing localStorage key "${key}":`, error);
    }
  }, [key, initialValue]);

  // Listen for changes from *other* browser tabs via native 'storage' event
  useEffect(() => {
    if (!syncCrossTab || typeof window === 'undefined') return;

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === key && event.newValue !== null) {
        try {
          setStoredValue(deserializer(event.newValue));
        } catch (error) {
          console.warn(`Error parsing sync payload for "${key}":`, error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [key, deserializer, syncCrossTab]);

  // Listen for changes from other components in the *same* tab
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleLocalChange = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail.key === key && customEvent.detail.newValue !== undefined) {
        setStoredValue(customEvent.detail.newValue);
      }
    };

    localStorageEventTarget?.addEventListener('local-storage', handleLocalChange);
    return () => localStorageEventTarget?.removeEventListener('local-storage', handleLocalChange);
  }, [key]);

  return [storedValue, setValue, removeValue];
}
