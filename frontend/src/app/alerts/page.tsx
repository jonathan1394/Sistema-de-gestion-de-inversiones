import { Page, SectionTitle, preStyle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { AlertsActions } from "./alerts-actions";

type AlertEntry = {
  timestamp: string;
  level: string;
  category: string;
  title: string;
  message: string;
  data?: Record<string, unknown> | null;
};

export default async function AlertsPage() {
  const history = await apiGet<AlertEntry[]>("/alerts/history?limit=200");
  const rules = await apiGet<Record<string, unknown>>("/alerts/rules");

  return (
    <Page
      title="Alerts"
      subtitle="Historial (GET /alerts/history) y reglas (GET /alerts/rules)"
      actions={<AlertsActions />}
    >
      <SectionTitle>Rules</SectionTitle>
      <pre style={preStyle}>{JSON.stringify(rules, null, 2)}</pre>

      <SectionTitle>History</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Timestamp</th>
              <th style={thStyle}>Level</th>
              <th style={thStyle}>Category</th>
              <th style={thStyle}>Title</th>
              <th style={thStyle}>Message</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td style={{ padding: 12, color: "#6b7280" }} colSpan={5}>
                  No hay alertas registradas.
                </td>
              </tr>
            ) : (
              history
                .slice()
                .reverse()
                .map((a, idx) => (
                  <tr key={`${a.timestamp}-${idx}`} style={{ borderTop: "1px solid #eef2f7" }}>
                    <td style={{ padding: 10, whiteSpace: "nowrap" }}>{a.timestamp}</td>
                    <td style={{ padding: 10, fontWeight: 800 }}>{a.level}</td>
                    <td style={{ padding: 10 }}>{a.category}</td>
                    <td style={{ padding: 10, fontWeight: 700 }}>{a.title}</td>
                    <td style={{ padding: 10, color: "#374151" }}>{a.message}</td>
                  </tr>
                ))
            )}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
