
// --- Safe useAsyncState Hook ---
import { useState, useCallback, useRef, useEffect } from 'react';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  /** A unique identifier representing the latest execution cycle */
  executionCount: number;
}

/**
 * A highly robust wrapper for executing asynchronous functions within React components.
 * 
 * Crucial Features:
 * 1. "Can't perform a React state update on an unmounted component" protection.
 *    It uses an `isMounted` ref to silently swallow state updates if the user 
 *    navigates away before the Promise resolves.
 * 2. Race condition protection. If the user clicks a button twice rapidly, 
 *    the first request's resolution is ignored in favor of the second request's payload.
 * 3. Exposes a clean `{ loading, error, data, execute }` paradigm.
 * 
 * @param asyncFunction The promise-returning function to wrap
 * @param immediate If true, runs the function immediately on mount
 * @returns The async state and an execute trigger
 */
export function useAsyncState<T, P extends unknown[]>(
  asyncFunction: (...args: P) => Promise<T>,
  immediate = false
) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: immediate,
    error: null,
    executionCount: 0,
  });

  // Track if component is mounted
  const isMountedRef = useRef(true);
  
  // Track the number of executions to prevent race conditions 
  // (where an older slow request overwrites a newer fast request)
  const executionCountRef = useRef(0);
  
  // Track the function so we don't need it in dependency arrays
  const asyncFunctionRef = useRef(asyncFunction);
  
  useEffect(() => {
    isMountedRef.current = true;
    asyncFunctionRef.current = asyncFunction;
    return () => {
      isMountedRef.current = false;
    };
  }, [asyncFunction]);

  const execute = useCallback(
    async (...args: P): Promise<T | null> => {
      executionCountRef.current += 1;
      const currentExecution = executionCountRef.current;

      setState((prevState) => ({
        ...prevState,
        loading: true,
        error: null,
        executionCount: currentExecution,
      }));

      try {
        const response = await asyncFunctionRef.current(...args);
        
        // Before updating state, check two things:
        // 1. Are we still mounted?
        // 2. Is this response from the LATEST execution?
        if (isMountedRef.current && currentExecution === executionCountRef.current) {
          setState({
            data: response,
            loading: false,
            error: null,
            executionCount: currentExecution,
          });
        }
        return response;
      } catch (error) {
        if (isMountedRef.current && currentExecution === executionCountRef.current) {
          setState({
            data: null,
            loading: false,
            error: error instanceof Error ? error : new Error(String(error)),
            executionCount: currentExecution,
          });
        }
        // Rethrow so the caller can catch it locally if they want
        throw error;
      }
    },
    []
  );

  // Support immediate execution on mount
  useEffect(() => {
    if (immediate) {
      // @ts-expect-error — execute() accepts any args; empty call is valid for parameter-free functions
      execute();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [immediate]);

  return {
    ...state,
    execute,
    /** Helper to reset the state back to pristine null */
    reset: useCallback(() => {
      if (isMountedRef.current) {
        setState({ data: null, loading: false, error: null, executionCount: executionCountRef.current });
      }
    }, [])
  };
}
