import { Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { DecisionEntry, AlertEntry } from "@/types";

function formatTimestamp(ts: string): string {
  if (!ts) return "-";

  const numericTs = Number(ts);
  if (Number.isFinite(numericTs)) {
    return new Date(numericTs).toLocaleString();
  }

  const parsed = new Date(ts);
  return Number.isNaN(parsed.getTime()) ? ts : parsed.toLocaleString();
}

export default async function LogsPage() {
  const [decisions, alerts] = await Promise.all([
    apiGet<DecisionEntry[]>("/decisions?limit=100").catch(() => []),
    apiGet<AlertEntry[]>("/alerts/history?limit=100").catch(() => []),
  ]);

  const logs: { ts: string; kind: string; level: string; msg: string }[] = [];

  for (const d of decisions) {
    logs.push({
      ts: d.timestamp,
      kind: "decision",
      level: d.approved ? "info" : "warn",
      msg: `[${d.mode}] ${d.symbol ?? "—"} ${d.decision_type} → ${d.approved ? "APPROVED" : "REJECTED"}: ${d.reason}${d.strategy_name ? ` (${d.strategy_name})` : ""}`,
    });
  }

  for (const a of alerts) {
    logs.push({
      ts: a.timestamp,
      kind: "alert",
      level: a.level === "critical" || a.level === "error" ? "error" : "info",
      msg: `[${a.category ?? a.level.toUpperCase()}] ${a.title}: ${a.message}`,
    });
  }

  logs.sort((a, b) => b.ts.localeCompare(a.ts));

  return (
    <Page title="Logs" subtitle={`${logs.length} entries — decisions + alerts`}>
      <SectionTitle>System activity</SectionTitle>

      {logs.length === 0 ? (
        <p style={{ color: "#6b7280", marginTop: 12 }}>No log entries found.</p>
      ) : (
        <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f9fafb", textAlign: "left" }}>
                <th style={thStyle}>Time</th>
                <th style={thStyle}>Level</th>
                <th style={thStyle}>Kind</th>
                <th style={thStyle}>Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((entry, i) => {
                const levelColor =
                  entry.level === "error" ? "#b91c1c" : entry.level === "warn" ? "#d97706" : "#059669";
                return (
                  <tr key={`${entry.kind}-${i}`} style={{ borderTop: "1px solid #eef2f7" }}>
                    <td style={{ padding: 10, color: "#6b7280", whiteSpace: "nowrap", fontSize: 11 }}>
                      {formatTimestamp(entry.ts)}
                    </td>
                    <td style={{ padding: 10 }}>
                      <span
                        style={{
                          background: levelColor,
                          color: "white",
                          borderRadius: 6,
                          padding: "2px 8px",
                          fontWeight: 700,
                          fontSize: 11,
                        }}
                      >
                        {entry.level.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: 10, fontWeight: 700 }}>{entry.kind}</td>
                    <td style={{ padding: 10, color: "#374151" }}>{entry.msg}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Page>
  );
}
