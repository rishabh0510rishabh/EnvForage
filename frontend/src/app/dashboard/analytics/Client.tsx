"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../../services/api";
import type { AnalyticsSummary } from "../../../types";
import { AuthProvider, useAuth } from "../../../auth/AuthProvider";
const COLORS = [
  "#6366f1",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#a855f7",
];

function toChartData(record: Record<string, number>) {
  return Object.entries(record).map(([name, value]) => ({ name, value }));
}

function HeatmapTable({
  data,
}: {
  data: AnalyticsSummary["cuda_version_heatmap"];
}) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-400">No CUDA data available yet.</p>;
  }

  const cudaVersions = Array.from(
    new Set(data.map((d) => d.cuda_version)),
  ).sort();
  const gpuNames = Array.from(new Set(data.map((d) => d.gpu_name))).sort();
  const lookup = new Map(
    data.map((d) => [`${d.cuda_version}|${d.gpu_name}`, d.count]),
  );
  const maxCount = Math.max(...data.map((d) => d.count));

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border-collapse">
        <thead>
          <tr>
            <th className="p-2 text-left border-b border-gray-700">
              CUDA \ GPU
            </th>
            {gpuNames.map((gpu) => (
              <th
                key={gpu}
                className="p-2 text-left border-b border-gray-700 whitespace-nowrap"
              >
                {gpu}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cudaVersions.map((cuda) => (
            <tr key={cuda}>
              <td className="p-2 font-medium border-b border-gray-800">
                {cuda}
              </td>
              {gpuNames.map((gpu) => {
                const count = lookup.get(`${cuda}|${gpu}`) ?? 0;
                const intensity = maxCount > 0 ? count / maxCount : 0;
                return (
                  <td
                    key={gpu}
                    className="p-2 border-b border-gray-800 text-center"
                    style={{
                      backgroundColor:
                        count > 0
                          ? `rgba(99, 102, 241, ${0.15 + intensity * 0.65})`
                          : "transparent",
                    }}
                  >
                    {count || ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FailuresTable({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1]);

  if (rows.length === 0) {
    return (
      <p className="text-sm text-gray-400">
        No compatibility failures recorded.
      </p>
    );
  }

  return (
    <table className="min-w-full text-sm">
      <thead>
        <tr>
          <th className="p-2 text-left border-b border-gray-700">Check</th>
          <th className="p-2 text-left border-b border-gray-700">Failures</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([name, count]) => (
          <tr key={name}>
            <td className="p-2 border-b border-gray-800">{name}</td>
            <td className="p-2 border-b border-gray-800">{count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/40 p-4">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      {children}
    </div>
  );
}

function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const { accessToken, isLoading: authLoading } = useAuth();

  useEffect(() => {
    if (authLoading) return;

    let cancelled = false;

    api
      .getAnalyticsSummary(accessToken ?? undefined)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, authLoading]);

  if (loading) {
    return <div className="p-8 text-gray-400">Loading analytics…</div>;
  }

  if (error || !data) {
    return (
      <div className="p-8 text-red-400">
        Failed to load analytics{error ? `: ${error}` : ""}.
      </div>
    );
  }

  const gpuData = toChartData(data.gpu_distribution);
  const pythonData = toChartData(data.python_version_histogram);
  const osData = toChartData(data.os_distribution);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-bold">Telemetry Analytics Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card title="GPU Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={gpuData}
                dataKey="value"
                nameKey="name"
                outerRadius={100}
                label
              >
                {gpuData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="OS Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={osData}
                dataKey="value"
                nameKey="name"
                innerRadius={60}
                outerRadius={100}
                label
              >
                {osData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Python Version Histogram">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={pythonData}>
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#6366f1" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Top 10 Compatibility Failures">
          <FailuresTable data={data.common_failures} />
        </Card>
      </div>

      <Card title="CUDA Version × GPU Model">
        <HeatmapTable data={data.cuda_version_heatmap} />
      </Card>
    </div>
  );
}

export default function Client() {
  return (
    <AuthProvider>
      <AnalyticsDashboard />
    </AuthProvider>
  );
}
