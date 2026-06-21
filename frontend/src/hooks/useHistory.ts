
// --- Advanced useHistory Hook ---
import { useState, useCallback } from 'react';

/**
 * Configuration options for the history stack.
 */
export interface UseHistoryOptions {
  /** Maximum number of states to remember. Default is 50. */
  capacity?: number;
}

export interface UseHistoryReturn<T> {
  /** The current active state */
  state: T;
  /** Sets a new state, pushing the old one to the undo stack and clearing redo */
  set: (newVal: T | ((prev: T) => T)) => void;
  /** Undo the last change */
  undo: () => void;
  /** Redo the last undone change */
  redo: () => void;
  /** True if an undo operation is possible */
  canUndo: boolean;
  /** True if a redo operation is possible */
  canRedo: boolean;
  /** Reverts the state completely to the initial state, clearing history */
  reset: () => void;
  /** Array of past states */
  past: ReadonlyArray<T>;
  /** Array of future states */
  future: ReadonlyArray<T>;
}

/**
 * A hook that augments standard `useState` with comprehensive Time-Travel capabilities.
 * Perfect for complex forms, drawing applications, or multi-step wizards that require 
 * robust Undo/Redo functionality without relying on a massive global Redux store.
 */
export function useHistory<T>(
  initialState: T | (() => T),
  options: UseHistoryOptions = {}
): UseHistoryReturn<T> {
  const { capacity = 50 } = options;

  // We only track the actual UI state with useState.
  // The past/future stacks are kept in refs to avoid excessive re-renders during setup.
  // However, because we want the UI to disable "Undo" buttons when empty, 
  // we do need to track the stack sizes in state.
  
  const [state, setState] = useState<T>(initialState);
  
  const [past, setPast] = useState<T[]>([]);
  const [future, setFuture] = useState<T[]>([]);

  const canUndo = past.length > 0;
  const canRedo = future.length > 0;

  const set = useCallback((newVal: T | ((prev: T) => T)) => {
    setState((currentState) => {
      // Evaluate if it's a function update
      const resolvedVal = newVal instanceof Function ? newVal(currentState) : newVal;
      
      // Don't clutter history if the value hasn't actually changed
      if (resolvedVal === currentState) return currentState;

      setPast((prevPast) => {
        const newPast = [...prevPast, currentState];
        // Enforce capacity constraint
        if (newPast.length > capacity) {
          return newPast.slice(newPast.length - capacity);
        }
        return newPast;
      });
      
      // When a new action is taken, the alternative future is obliterated
      setFuture([]);
      
      return resolvedVal;
    });
  }, [capacity]);

  const undo = useCallback(() => {
    if (!canUndo) return;

    setState((currentState) => {
      const previousState = past[past.length - 1];
      
      setPast((prevPast) => prevPast.slice(0, prevPast.length - 1));
      setFuture((prevFuture) => [currentState, ...prevFuture]);
      
      return previousState;
    });
  }, [canUndo, past]);

  const redo = useCallback(() => {
    if (!canRedo) return;

    setState((currentState) => {
      const nextState = future[0];
      
      setPast((prevPast) => [...prevPast, currentState]);
      setFuture((prevFuture) => prevFuture.slice(1));
      
      return nextState;
    });
  }, [canRedo, future]);

  const reset = useCallback(() => {
    const resolvedInitial = initialState instanceof Function ? initialState() : initialState;
    setState(resolvedInitial);
    setPast([]);
    setFuture([]);
  }, [initialState]);

  return {
    state,
    set,
    undo,
    redo,
    canUndo,
    canRedo,
    reset,
    past,
    future,
  };
}

/**
 * A simpler derivative hook that ONLY tracks the previous value.
 * Useful for transition animations or differential logic.
 */
export function usePrevious<T>(value: T): T | undefined {
  const [prev, setPrev] = useState<T | undefined>(undefined);
  const [curr, setCurr] = useState<T>(value);

  // Detect when the value changes and update in an effect (not during render)
  if (curr !== value) {
    // Synchronously flush both updates before the next paint
    // This is safe because we're not in a React effect — we're detecting
    // a render-time derived state change (React's documented pattern).
    setCurr(value);
    setPrev(curr);
  }

  return prev;
}
