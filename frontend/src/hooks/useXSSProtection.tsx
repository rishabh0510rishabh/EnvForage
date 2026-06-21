"use client";

/**
 * useXSSProtection — React hook for safe HTML rendering.
 *
 * Wraps the project's `sanitizeHtml` utility and exposes a stable
 * `sanitize` function so any component that needs to render
 * potentially-unsafe HTML (e.g. from the backend or user input) can do so
 * safely via `dangerouslySetInnerHTML`.
 *
 * Usage:
 *   const { sanitize } = useXSSProtection();
 *   <div dangerouslySetInnerHTML={{ __html: sanitize(rawHtml) }} />
 */

import { useCallback } from "react";
import { sanitizeHtml, type SanitizeConfig } from "../utils/sanitize";

export interface UseXSSProtectionReturn {
  /**
   * Sanitise a potentially-unsafe HTML string.
   *
   * @param html   Raw HTML string (may be null/undefined — returns '' in that case)
   * @param config Optional strictness overrides (see SanitizeConfig)
   * @returns      A guaranteed-safe HTML string
   */
  sanitize: (html: string | null | undefined, config?: SanitizeConfig) => string;
}

/**
 * Hook that provides a stable `sanitize` helper for XSS-safe HTML rendering.
 *
 * The returned `sanitize` reference is memoised with `useCallback` so it
 * does **not** trigger unnecessary re-renders in child components.
 */
export default function useXSSProtection(): UseXSSProtectionReturn {
  const sanitize = useCallback(
    (html: string | null | undefined, config?: SanitizeConfig): string =>
      sanitizeHtml(html, config),
    [],
  );

  return { sanitize };
}
