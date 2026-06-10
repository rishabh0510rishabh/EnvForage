
// --- Advanced useClickOutside Hook ---
import { useEffect, useRef, RefObject } from 'react';

type AnyEvent = MouseEvent | TouchEvent;

/**
 * A highly resilient hook that triggers a callback when a user clicks outside 
 * of a specified element (or array of elements).
 * 
 * Features:
 * - Supports multiple refs (e.g. clicking a dropdown OR its trigger button shouldn't close it)
 * - Listens to both mousedown and touchstart for mobile compatibility
 * - Gracefully ignores clicks on disconnected nodes (often happens with rapid React unmounts)
 * 
 * @param ref A React ref or array of refs to monitor
 * @param handler Callback to execute when a click lands outside the ref(s)
 * @param enabled Optional flag to pause the listener (performance optimization)
 */
export function useClickOutside<T extends HTMLElement = HTMLElement>(
  ref: RefObject<T> | RefObject<T>[],
  handler: (event: AnyEvent) => void,
  enabled: boolean = true
): void {
  
  // Use a ref for the handler to avoid re-binding the event listener if the handler function identity changes
  const handlerRef = useRef(handler);
  
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    const listener = (event: AnyEvent) => {
      const target = event.target as Node;
      
      // If the target is no longer in the document (e.g., an element was removed from the DOM
      // exactly during this click event cycle), we ignore it to prevent false positive closures.
      if (!target || !document.contains(target)) {
        return;
      }

      // Normalize single ref vs array of refs
      const refs = Array.isArray(ref) ? ref : [ref];

      // Check if the click landed INSIDE any of our monitored refs
      const isInside = refs.some((r) => {
        return r.current && r.current.contains(target);
      });

      // If it's NOT inside, it's outside. Trigger the handler.
      if (!isInside) {
        handlerRef.current(event);
      }
    };

    // We bind to `mousedown` and `touchstart` instead of `click`.
    // Why? If a user clicks inside a modal, drags their mouse OUTSIDE the modal, 
    // and releases, `click` fires on the document but we shouldn't close the modal.
    document.addEventListener('mousedown', listener, { passive: true });
    document.addEventListener('touchstart', listener, { passive: true });
    
    // Listen for iframe clicks. If focus shifts to an iframe, we treat it as an outside click.
    const blurListener = () => {
      if (document.activeElement && document.activeElement.tagName === 'IFRAME') {
        // We synthesize a fake event since we can't get the real mouse event inside the iframe
        handlerRef.current(new MouseEvent('mousedown'));
      }
    };
    window.addEventListener('blur', blurListener);

    return () => {
      document.removeEventListener('mousedown', listener);
      document.removeEventListener('touchstart', listener);
      window.removeEventListener('blur', blurListener);
    };
  }, [ref, enabled]);
}
