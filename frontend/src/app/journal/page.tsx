import { Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { PortfolioTrade } from "@/types";

function fmtMoney(v: number): string {
  if (!Number.isFinite(v)) return "-";
  return `${v >= 0 ? "+" : ""}$${v.toFixed(2)}`;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "-";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}

export default async function JournalPage() {
  const trades = await apiGet<PortfolioTrade[]>("/portfolio/trades?limit=500").catch(() => []);

  const totalPnL = trades.reduce((s, t) => s + (t.pnl ?? 0), 0);
  const wins = trades.filter((t) => (t.pnl ?? 0) > 0);
  const losses = trades.filter((t) => (t.pnl ?? 0) < 0);
  const winRate = trades.length ? wins.length / trades.length : 0;
  const avgWin = wins.length ? wins.reduce((s, t) => s + (t.pnl ?? 0), 0) / wins.length : 0;
  const avgLoss = losses.length ? losses.reduce((s, t) => s + (t.pnl ?? 0), 0) / losses.length : 0;

  return (
    <Page title="Journal" subtitle={`${trades.length} paper trades registrados — PnL total: ${fmtMoney(totalPnL)}`}>
      {trades.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
          <Metric label="Total trades" value={String(trades.length)} />
          <Metric label="Win rate" value={fmtPct(winRate)} />
          <Metric label="Avg win" value={fmtMoney(avgWin)} />
          <Metric label="Avg loss" value={fmtMoney(avgLoss)} />
          <Metric label="Total PnL" value={fmtMoney(totalPnL)} />
        </div>
      )}

      <SectionTitle>Trade history</SectionTitle>

      {trades.length === 0 ? (
        <p style={{ color: "#6b7280", marginTop: 12 }}>No trades found. Start paper trading to see entries here.</p>
      ) : (
        <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f9fafb", textAlign: "left" }}>
                <th style={thStyle}>ID</th>
                <th style={thStyle}>Symbol</th>
                <th style={thStyle}>Action</th>
                <th style={thStyle}>Qty</th>
                <th style={thStyle}>Price</th>
                <th style={thStyle}>Commission</th>
                <th style={thStyle}>PnL</th>
                <th style={thStyle}>PnL%</th>
                <th style={thStyle}>Reason</th>
                <th style={thStyle}>Date</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => {
                const pnlColor = (t.pnl ?? 0) > 0 ? "#059669" : (t.pnl ?? 0) < 0 ? "#b91c1c" : "#6b7280";
                return (
                  <tr key={t.id} style={{ borderTop: "1px solid #eef2f7" }}>
                    <td style={{ padding: 10, color: "#6b7280" }}>{t.id}</td>
                    <td style={{ padding: 10, fontWeight: 700 }}>{t.symbol}</td>
                    <td style={{ padding: 10 }}>{t.action}</td>
                    <td style={{ padding: 10 }}>{t.quantity}</td>
                    <td style={{ padding: 10 }}>${t.price.toFixed(2)}</td>
                    <td style={{ padding: 10 }}>{t.commission ? `$${t.commission.toFixed(4)}` : "-"}</td>
                    <td style={{ padding: 10, fontWeight: 700, color: pnlColor }}>{fmtMoney(t.pnl)}</td>
                    <td style={{ padding: 10, color: pnlColor }}>{fmtPct(t.pnl_pct)}</td>
                    <td style={{ padding: 10, color: "#374151", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.reason ?? "-"}</td>
                    <td style={{ padding: 10, color: "#6b7280", whiteSpace: "nowrap" }}>{t.created_at ? new Date(t.created_at).toLocaleString() : "-"}</td>
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12 }}>
      <div style={{ color: "#6b7280", fontSize: 11, fontWeight: 700 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}
