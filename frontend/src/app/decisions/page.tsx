import { Page, SectionTitle, preStyle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { DecisionsActions } from "./decisions-actions";

type Decision = {
  decision_id: string;
  decision_type: string;
  timestamp: string;
  symbol?: string | null;
  strategy_name?: string | null;
  timeframe?: string | null;
  mode: string;
  approved: boolean;
  reason: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  policy_version?: string | null;
  strategy_version?: string | null;
};

export default async function DecisionsPage() {
  const decisions = await apiGet<Decision[]>("/decisions?limit=200");

  return (
    <Page title="Decisions" subtitle="Últimas decisiones (GET /decisions)" actions={<DecisionsActions />}>
      <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Time (ms UTC)</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Symbol</th>
              <th style={thStyle}>Approved</th>
              <th style={thStyle}>Reason</th>
              <th style={thStyle}>ID</th>
            </tr>
          </thead>
          <tbody>
            {decisions.length === 0 ? (
              <tr>
                <td style={{ padding: 12, color: "#6b7280" }} colSpan={6}>
                  No hay decisiones registradas.
                </td>
              </tr>
            ) : (
              decisions.map((d) => (
                <tr key={d.decision_id} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td style={{ padding: 10, whiteSpace: "nowrap" }}>{d.timestamp}</td>
                  <td style={{ padding: 10, fontWeight: 800 }}>{d.decision_type}</td>
                  <td style={{ padding: 10, fontWeight: 700 }}>{d.symbol ?? "-"}</td>
                  <td style={{ padding: 10, fontWeight: 800, color: d.approved ? "#065f46" : "#b91c1c" }}>
                    {d.approved ? "YES" : "NO"}
                  </td>
                  <td style={{ padding: 10, color: "#374151" }}>{d.reason}</td>
                  <td style={{ padding: 10, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 12 }}>
                    {d.decision_id}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <details style={{ marginTop: 12 }}>
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>Ver payload JSON (debug)</summary>
        <pre style={preStyle}>{JSON.stringify(decisions, null, 2)}</pre>
      </details>
    </Page>
  );
}
