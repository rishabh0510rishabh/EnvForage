// This file is the Next.js App Router client instrumentation hook.
// Sentry is already initialised in sentry.client.config.ts — do NOT call
// Sentry.init here again to avoid double-initialisation.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

// Export the router transition hook so Sentry can capture navigation spans.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
