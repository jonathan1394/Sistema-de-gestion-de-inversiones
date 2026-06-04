"use client";

import { useState, useTransition } from "react";

import { Badge, tdStyle, thStyle } from "@/app/components/ui";
import { apiPost } from "@/lib/api";

type Prospect = {
  symbol: string;
  interval: string;
  status: string;
  score: number;
  trend?: string | null;
  volatility?: string | null;
  volume_profile?: string | null;
  rsi_condition?: string | null;
  signals_count: number;
  notes: string;
};

export function ProspectsList({ prospects }: { prospects: Prospect[] }) {
  const [pendingSymbol, setPendingSymbol] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  async function updateStatus(symbol: string, interval: string, status: string) {
    setPendingSymbol(symbol);
    await apiPost("/prospecting/prospects/status", { symbol, interval, status });
    window.location.reload();
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th style={thStyle}>Symbol</th>
          <th style={thStyle}>Interval</th>
          <th style={thStyle}>Status</th>
          <th style={thStyle}>Score</th>
          <th style={thStyle}>Trend</th>
          <th style={thStyle}>Signals</th>
          <th style={thStyle}>Notes</th>
          <th style={thStyle}>Action</th>
        </tr>
      </thead>
      <tbody>
        {prospects.length === 0 ? (
          <tr>
            <td className="empty-state" colSpan={8}>
              No prospects found for the current filters.
            </td>
          </tr>
        ) : (
          prospects.map((p) => (
            <tr key={`${p.symbol}-${p.interval}`}>
              <td style={{ ...tdStyle, fontWeight: 800 }}>{p.symbol}</td>
              <td style={tdStyle}>{p.interval}</td>
              <td style={tdStyle}><StatusBadge status={p.status} /></td>
              <td style={{ ...tdStyle, fontWeight: 700 }}>{p.score.toFixed(4)}</td>
              <td style={tdStyle}>{p.trend ?? "-"}</td>
              <td style={tdStyle}>{p.signals_count}</td>
              <td style={{ ...tdStyle, color: "var(--muted)" }}>{p.notes || "-"}</td>
              <td style={tdStyle}>
                <select
                  className="select"
                  defaultValue={p.status}
                  disabled={pendingSymbol === p.symbol}
                  onChange={(e) => {
                    const nextStatus = e.target.value;
                    startTransition(() => {
                      updateStatus(p.symbol, p.interval, nextStatus).catch(() => {
                        setPendingSymbol(null);
                      });
                    });
                  }}
                >
                  <option value="watching">watching</option>
                  <option value="active">active</option>
                  <option value="archived">archived</option>
                </select>
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "active") return <Badge tone="success">active</Badge>;
  if (status === "archived") return <Badge tone="danger">archived</Badge>;
  return <Badge tone="warning">watching</Badge>;
}
