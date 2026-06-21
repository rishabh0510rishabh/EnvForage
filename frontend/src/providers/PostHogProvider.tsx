"use client";

/**
 * PostHogProvider — Anonymous telemetry bootstrap.
 *
 * Initialises PostHog on the client side once the app mounts.
 * Designed to be mounted once in the root layout as a wrapper.
 *
 * If NEXT_PUBLIC_POSTHOG_KEY is not set, telemetry is silently disabled.
 */

import { useEffect } from "react";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://app.posthog.com";

export default function PostHogProvider() {
  useEffect(() => {
    if (!POSTHOG_KEY) {
      // Telemetry disabled — key not configured
      return;
    }

    // Dynamic import keeps PostHog out of the server bundle entirely.
    import("posthog-js")
      .then(({ default: posthog }) => {
        if (!posthog.__loaded) {
          posthog.init(POSTHOG_KEY, {
            api_host: POSTHOG_HOST,
            // Respect user privacy — disable autocapture in favour of manual events
            autocapture: false,
            // Do not capture PII
            capture_pageview: false,
            // Persist anonymised session across tabs
            persistence: "localStorage+cookie",
          });
        }
      })
      .catch(() => {
        // PostHog not installed — gracefully ignore
      });
  }, []);

  // This provider renders nothing; it is a side-effect-only component.
  return null;
}
