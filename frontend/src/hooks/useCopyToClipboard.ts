
// --- Advanced useCopyToClipboard Hook ---
import { useState, useCallback, useEffect, useRef } from 'react';

export interface CopyToClipboardState {
  value: string | null;
  error: Error | null;
  isCopied: boolean;
}

export interface CopyToClipboardOptions {
  /** How long the `isCopied` flag stays true before resetting (ms). Default: 2000 */
  resetTimeout?: number;
}

/**
 * An advanced hook for copying text to the clipboard.
 * Features:
 * - Uses the modern navigator.clipboard API
 * - Graceful fallback to document.execCommand for older browsers / HTTP environments
 * - Manages an ephemeral `isCopied` state that resets after a timeout
 * - Returns detailed error states
 * 
 * @param options Configuration options
 * @returns [state, copyFunction] tuple
 */
export function useCopyToClipboard(
  options: CopyToClipboardOptions = {}
): [CopyToClipboardState, (text: string) => Promise<boolean>] {
  const { resetTimeout = 2000 } = options;
  
  const [state, setState] = useState<CopyToClipboardState>({
    value: null,
    error: null,
    isCopied: false,
  });

  const resetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (resetTimeoutRef.current) {
        clearTimeout(resetTimeoutRef.current);
      }
    };
  }, []);

  const copyToClipboard = useCallback(
    async (text: string): Promise<boolean> => {
      // Clear previous timeout if user clicks multiple times rapidly
      if (resetTimeoutRef.current) {
        clearTimeout(resetTimeoutRef.current);
      }

      const updateCopiedState = (success: boolean, error: Error | null = null) => {
        setState({
          value: success ? text : null,
          error,
          isCopied: success,
        });

        if (success) {
          resetTimeoutRef.current = setTimeout(() => {
            setState((prev) => ({ ...prev, isCopied: false }));
          }, resetTimeout);
        }
      };

      if (!text) {
        updateCopiedState(false, new Error('Cannot copy empty text'));
        return false;
      }

      // Try modern async Clipboard API first
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(text);
          updateCopiedState(true);
          return true;
        } catch (error) {
          // If the modern API fails (e.g. lack of Permissions), fall through to the legacy method
          console.warn('navigator.clipboard failed, attempting legacy fallback.', error);
        }
      }

      // Fallback: Legacy execCommand method (works without HTTPS sometimes, or in older Safari)
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        
        // Prevent scrolling to bottom of page in MS Edge
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '0';
        
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);

        if (successful) {
          updateCopiedState(true);
          return true;
        } else {
          updateCopiedState(false, new Error('execCommand returned false'));
          return false;
        }
      } catch (error) {
        updateCopiedState(false, error instanceof Error ? error : new Error('Unknown error during copy'));
        return false;
      }
    },
    [resetTimeout]
  );

  return [state, copyToClipboard];
}
