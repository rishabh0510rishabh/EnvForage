"use client";

/**
 * useAIStream — React hook for consuming server-sent streaming responses.
 *
 * Wraps the backend `/troubleshoot` stream call and exposes reactive state
 * (`loading`, `streamingText`, `error`, `result`) to any component that
 * drives the AI troubleshoot UX.
 *
 * Usage:
 *   const { stream, loading, streamingText, error, result, reset } = useAIStream();
 *   await stream({ diagnostic, profile_slug, user_description });
 */

import { useCallback, useRef, useState } from "react";
import { api } from "../services/api";
import type {
  TroubleshootRequest,
  TroubleshootResponse,
} from "../types";

// ── Types ────────────────────────────────────────────────────────────────────

export interface UseAIStreamState {
  /** Whether a streaming request is currently in-flight. */
  loading: boolean;
  /** Raw text tokens accumulated from the live stream. */
  streamingText: string;
  /** Error message if the request failed, otherwise null. */
  error: string | null;
  /** Final structured result returned once streaming completes. */
  result: TroubleshootResponse | null;
}

export interface UseAIStreamReturn extends UseAIStreamState {
  /**
   * Fire off a troubleshoot stream request.
   * Automatically resets previous state before starting.
   *
   * @param request  The troubleshoot payload (diagnostic + optional fields)
   */
  stream: (request: TroubleshootRequest) => Promise<void>;
  /**
   * Reset all state back to the initial idle condition.
   * Useful for "New Analysis" / retry flows.
   */
  reset: () => void;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Manages the lifecycle of a single AI troubleshoot streaming request.
 *
 * State transitions:
 *   idle  →  loading + streaming  →  result (success) | error (failure)  →  idle (reset)
 */
export default function useAIStream(): UseAIStreamReturn {
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TroubleshootResponse | null>(null);

  // Ref-based abort guard so we can cancel stale streams if the component unmounts
  const abortedRef = useRef(false);

  const reset = useCallback(() => {
    abortedRef.current = false;
    setLoading(false);
    setStreamingText("");
    setError(null);
    setResult(null);
  }, []);

  const stream = useCallback(async (request: TroubleshootRequest) => {
    // Reset to a clean state before starting
    abortedRef.current = false;
    setError(null);
    setResult(null);
    setStreamingText("");
    setLoading(true);

    try {
      const response = await api.troubleshoot(request, (token) => {
        if (!abortedRef.current) {
          setStreamingText((prev) => prev + token);
        }
      });

      if (!abortedRef.current) {
        setResult(response);
      }
    } catch (err) {
      if (!abortedRef.current) {
        setError(
          err instanceof Error
            ? err.message
            : "AI troubleshooting failed. Check that the backend is running.",
        );
      }
    } finally {
      if (!abortedRef.current) {
        setLoading(false);
        // Clear the streaming preview once we have the structured result
        setStreamingText("");
      }
    }
  }, []);

  return { loading, streamingText, error, result, stream, reset };
}
