// This file configures the initialization of Sentry for edge features (middleware, edge routes, and so on).
// The config you add here will be used whenever one of the edge features is loaded.
// Note that this config is unrelated to the Vercel Edge Runtime and is also required when running locally.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const isProd = process.env.NODE_ENV === "production";

Sentry.init({
  dsn: "https://332a05f585f27f638437c375ff871def@o4511496226734080.ingest.us.sentry.io/4511496480423936",

  // Low sampling in production; full sampling in development for debugging.
  // Override via SENTRY_TRACES_SAMPLE_RATE env var if needed.
  tracesSampleRate: isProd
    ? parseFloat(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0.01")
    : 1,

  // Only forward logs to Sentry outside production (or when explicitly opted in).
  enableLogs: process.env.SENTRY_ENABLE_LOGS === "true" || !isProd,

  // Only send PII when explicitly opted in via env flag.
  sendDefaultPii: process.env.SENTRY_SEND_DEFAULT_PII === "true",
});
