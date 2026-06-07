// This file configures the initialization of Sentry on the browser/client.
// The config here is the single source of truth for client-side Sentry — do NOT
// call Sentry.init again in instrumentation-client.ts.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const isProd = process.env.NODE_ENV === "production";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  debug: false,

  // Add optional integrations for additional features
  integrations: [Sentry.replayIntegration()],

  // Low sampling in production; full sampling in development for debugging.
  // Override via NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE if needed.
  tracesSampleRate: isProd
    ? parseFloat(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.05")
    : 1,

  // Only forward logs to Sentry outside production (or when explicitly opted in).
  enableLogs: process.env.NEXT_PUBLIC_SENTRY_ENABLE_LOGS === "true" || !isProd,

  // Session replay: low baseline, higher on errors.
  replaysSessionSampleRate: isProd ? 0.05 : 0.1,
  replaysOnErrorSampleRate: isProd ? 0.2 : 1.0,

  // Do NOT send PII by default; opt in via env flag.
  sendDefaultPii: process.env.NEXT_PUBLIC_SENTRY_SEND_DEFAULT_PII === "true",
});
