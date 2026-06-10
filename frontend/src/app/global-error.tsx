"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body style={{ backgroundColor: "var(--bg-core)" }}>
        <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', textAlign: 'center', padding: '0 1rem' }}>
          <h1
            style={{
              fontSize: "clamp(2.5rem, 5vw, 4rem)",
              fontWeight: 900,
              color: "var(--text-primary)",
              marginBottom: "1rem",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            Critical System Error!
          </h1>
          <p
            style={{
              fontSize: "1.25rem",
              color: "var(--text-secondary)",
              marginBottom: "3rem",
              maxWidth: "500px",
              fontFamily: "var(--font-outfit), sans-serif",
            }}
          >
            We&apos;ve been notified of this issue and our team is looking into it.
          </p>
          <button
            onClick={() => reset()}
            style={{
              display: "inline-block",
              padding: "1rem 2.5rem",
              borderRadius: "8px",
              background: "var(--brand-primary)",
              color: "var(--text-inverse)",
              fontWeight: 600,
              fontSize: "1.125rem",
              border: "none",
              cursor: "pointer",
              transition: "all 0.2s ease",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            Refresh Page
          </button>
        </div>
      </body>
    </html>
  );
}
