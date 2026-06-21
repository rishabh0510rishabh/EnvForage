"use client";

/**
 * Webhook Logs — Settings page for viewing recent webhook delivery attempts.
 *
 * Displays a table of recent webhook delivery events with status, timestamp,
 * and a preview of the request/response payload.
 */

import { useState, useEffect } from "react";

interface WebhookLog {
  id: string;
  endpoint: string;
  status: "success" | "failed" | "pending";
  statusCode: number | null;
  triggeredAt: string;
  durationMs: number | null;
}

const MOCK_LOGS: WebhookLog[] = [
  { id: "wh_1", endpoint: "https://example.com/hook", status: "success", statusCode: 200, triggeredAt: "2026-06-19T10:30:00Z", durationMs: 142 },
  { id: "wh_2", endpoint: "https://example.com/hook", status: "failed", statusCode: 500, triggeredAt: "2026-06-19T09:12:00Z", durationMs: 8003 },
  { id: "wh_3", endpoint: "https://staging.example.com/hook", status: "success", statusCode: 200, triggeredAt: "2026-06-19T08:05:00Z", durationMs: 211 },
];

function StatusBadge({ status }: { status: WebhookLog["status"] }) {
  const colors: Record<WebhookLog["status"], string> = {
    success: "color: #22c55e; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3)",
    failed: "color: #ef4444; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3)",
    pending: "color: #f59e0b; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3)",
  };
  return (
    <span style={{ ...Object.fromEntries(colors[status].split(";").map(s => { const [k, v] = s.split(":"); return [k.trim().replace(/-([a-z])/g, (_, c: string) => c.toUpperCase()), v?.trim()]; }).filter(([k]) => k)), padding: "0.2rem 0.6rem", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 600 }}>
      {status}
    </span>
  );
}

export default function WebhookLogsPage() {
  const [logs, setLogs] = useState<WebhookLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate async data load
    const timer = setTimeout(() => {
      setLogs(MOCK_LOGS);
      setIsLoading(false);
    }, 400);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div style={{ padding: "2rem", maxWidth: "900px" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 800, marginBottom: "0.5rem", color: "var(--text-primary)" }}>
        Webhook Logs
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}>
        Recent delivery attempts for your configured webhook endpoints.
      </p>

      {isLoading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading logs…</p>
      ) : logs.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>No webhook deliveries recorded yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
              {["Endpoint", "Status", "HTTP Code", "Duration", "Triggered At"].map((h) => (
                <th key={h} style={{ padding: "0.75rem 1rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "0.75rem 1rem", color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>
                  {log.endpoint}
                </td>
                <td style={{ padding: "0.75rem 1rem" }}>
                  <StatusBadge status={log.status} />
                </td>
                <td style={{ padding: "0.75rem 1rem", color: "var(--text-secondary)" }}>
                  {log.statusCode ?? "—"}
                </td>
                <td style={{ padding: "0.75rem 1rem", color: "var(--text-secondary)" }}>
                  {log.durationMs != null ? `${log.durationMs}ms` : "—"}
                </td>
                <td style={{ padding: "0.75rem 1rem", color: "var(--text-muted)" }}>
                  {new Date(log.triggeredAt).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
