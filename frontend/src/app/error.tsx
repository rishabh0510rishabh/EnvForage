"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Runtime error caught by boundary:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '70vh', textAlign: 'center', padding: '0 1rem' }}>
      <AlertTriangle size={64} color="#ef4444" style={{ marginBottom: "2rem" }} />
      <h1
        style={{
          fontSize: "clamp(2.5rem, 5vw, 4rem)",
          fontWeight: 900,
          color: "var(--text-primary)",
          marginBottom: "1rem",
        }}
      >
        Something went wrong!
      </h1>
      <p
        style={{
          fontSize: "1.25rem",
          color: "var(--text-secondary)",
          marginBottom: "3rem",
          maxWidth: "500px",
        }}
      >
        An unexpected error occurred while loading this page.
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
        }}
      >
        Try again
      </button>
    </div>
  );
}
