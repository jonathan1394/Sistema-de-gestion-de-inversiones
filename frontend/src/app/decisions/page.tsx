import { Badge, Page, Panel, TableWrap, preStyle, thStyle, tdStyle } from "@/app/components/ui";
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

export default async function DecisionsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const page = typeof params.page === "string" ? Math.max(1, Number(params.page) || 1) : 1;
  const symbol = typeof params.symbol === "string" ? params.symbol : "";
  const approvedOnly = params.approved_only === "true";
  const rejectedOnly = params.rejected_only === "true";

  const query = new URLSearchParams({ page: String(page), limit: "50" });
  if (symbol) query.set("symbol", symbol);
  if (approvedOnly) query.set("approved_only", "true");
  if (rejectedOnly) query.set("rejected_only", "true");

  const decisions = await apiGet<Decision[]>(`/decisions?${query.toString()}`);

  return (
    <Page
      title="Decisions"
      subtitle="Últimas decisiones (GET /decisions)"
      actions={
        <DecisionsActions
          initialSymbol={symbol}
          initialApprovedOnly={approvedOnly}
          initialRejectedOnly={rejectedOnly}
          initialPage={page}
        />
      }
    >
      <Panel title="Trazabilidad de decisiones y aprobaciones">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
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
                  <td className="empty-state" colSpan={6}>
                    No hay decisiones registradas.
                  </td>
                </tr>
              ) : (
                decisions.map((d) => (
                  <tr key={d.decision_id}>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{d.timestamp}</td>
                    <td style={{ ...tdStyle, fontWeight: 800 }}>{d.decision_type}</td>
                    <td style={{ ...tdStyle, fontWeight: 700 }}>{d.symbol ?? "-"}</td>
                    <td style={tdStyle}><Badge tone={d.approved ? "success" : "danger"}>{d.approved ? "YES" : "NO"}</Badge></td>
                    <td style={{ ...tdStyle, color: "var(--muted)" }}>{d.reason}</td>
                    <td style={{ ...tdStyle, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 12 }}>
                      {d.decision_id}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </TableWrap>
      </Panel>

      <details style={{ marginTop: 12 }}>
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>Ver payload JSON (debug)</summary>
        <pre style={preStyle}>{JSON.stringify(decisions, null, 2)}</pre>
      </details>
    </Page>
  );
}
