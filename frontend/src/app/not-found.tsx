import Link from "next/link";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '70vh', textAlign: 'center', padding: '0 1rem' }}>
      <AlertCircle size={64} color="var(--brand-secondary)" style={{ marginBottom: "2rem" }} />
      <h1
        style={{
          fontSize: "clamp(3rem, 6vw, 5rem)",
          fontWeight: 900,
          color: "var(--text-primary)",
          marginBottom: "1rem",
        }}
      >
        404
      </h1>
      <h2
        style={{
          fontSize: "2rem",
          fontWeight: 700,
          color: "var(--text-primary)",
          marginBottom: "1.5rem",
        }}
      >
        Page not found
      </h2>
      <p
        style={{
          fontSize: "1.25rem",
          color: "var(--text-secondary)",
          marginBottom: "3rem",
          maxWidth: "500px",
        }}
      >
        We couldn&apos;t find the environment or page you were looking for. It might have been moved or deleted.
      </p>
      <Link
        href="/"
        style={{
          display: "inline-block",
          padding: "1rem 2.5rem",
          borderRadius: "8px",
          background: "var(--brand-primary)",
          color: "var(--text-inverse)",
          fontWeight: 600,
          fontSize: "1.125rem",
          textDecoration: "none",
          transition: "all 0.2s ease",
        }}
      >
        Return Home
      </Link>
    </div>
  );
}
