import { Card, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
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
        <div className="stats-grid">
          <Card label="Total trades" value={String(trades.length)} />
          <Card label="Win rate" value={fmtPct(winRate)} />
          <Card label="Avg win" value={fmtMoney(avgWin)} />
          <Card label="Avg loss" value={fmtMoney(avgLoss)} />
          <Card label="Total PnL" value={fmtMoney(totalPnL)} />
        </div>
      )}

      <SectionTitle>Trade history</SectionTitle>

      {trades.length === 0 ? (
        <p style={{ color: "var(--muted)", marginTop: 12 }}>No trades found. Start paper trading to see entries here.</p>
      ) : (
        <Panel title="Historial completo de operaciones paper">
          <TableWrap>
          <table className="data-table" style={{ fontSize: 12 }}>
            <thead>
              <tr>
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
                const pnlColor = (t.pnl ?? 0) > 0 ? "#86efac" : (t.pnl ?? 0) < 0 ? "#fca5a5" : "#94a3b8";
                return (
                  <tr key={t.id}>
                    <td style={{ ...tdStyle, color: "var(--muted)" }}>{t.id}</td>
                    <td style={{ ...tdStyle, fontWeight: 700 }}>{t.symbol}</td>
                    <td style={tdStyle}>{t.action}</td>
                    <td style={tdStyle}>{t.quantity}</td>
                    <td style={tdStyle}>${t.price.toFixed(2)}</td>
                    <td style={tdStyle}>{t.commission ? `$${t.commission.toFixed(4)}` : "-"}</td>
                    <td style={{ ...tdStyle, fontWeight: 700, color: pnlColor }}>{fmtMoney(t.pnl)}</td>
                    <td style={{ ...tdStyle, color: pnlColor }}>{fmtPct(t.pnl_pct)}</td>
                    <td style={{ ...tdStyle, color: "var(--muted)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.reason ?? "-"}</td>
                    <td style={{ ...tdStyle, color: "var(--muted)", whiteSpace: "nowrap" }}>{t.created_at ? new Date(t.created_at).toLocaleString() : "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </TableWrap>
        </Panel>
      )}
    </Page>
  );
}
