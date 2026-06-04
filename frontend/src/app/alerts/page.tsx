import { Badge, Page, Panel, SectionTitle, TableWrap, preStyle, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { AlertsActions } from "./alerts-actions";
import { RulesEditor } from "./rules-editor";

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
      <Panel title="Reglas activas del sistema de alertas">
        <RulesEditor initialRules={rules} />
        <pre style={preStyle}>{JSON.stringify(rules, null, 2)}</pre>
      </Panel>

      <SectionTitle>History</SectionTitle>
      <Panel title="Eventos registrados recientemente">
        <TableWrap>
          <table className="data-table">
          <thead>
            <tr>
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
                <td className="empty-state" colSpan={5}>
                  No hay alertas registradas.
                </td>
              </tr>
            ) : (
              history
                .slice()
                .reverse()
                .map((a, idx) => (
                  <tr key={`${a.timestamp}-${idx}`}>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{a.timestamp}</td>
                    <td style={tdStyle}><LevelBadge value={a.level} /></td>
                    <td style={tdStyle}>{a.category}</td>
                    <td style={{ ...tdStyle, fontWeight: 700 }}>{a.title}</td>
                    <td style={{ ...tdStyle, color: "var(--muted)" }}>{a.message}</td>
                  </tr>
                ))
            )}
          </tbody>
          </table>
        </TableWrap>
      </Panel>
    </Page>
  );
}

function LevelBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  if (normalized.includes("error") || normalized.includes("critical")) return <Badge tone="danger">{value}</Badge>;
  if (normalized.includes("warn")) return <Badge tone="warning">{value}</Badge>;
  if (normalized.includes("trade")) return <Badge tone="success">{value}</Badge>;
  return <Badge tone="info">{value}</Badge>;
}
