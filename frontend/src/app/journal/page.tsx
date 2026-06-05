import { Card, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet, apiPost } from "@/lib/api";
import type { PortfolioTrade } from "@/types";

type JournalAnalysis = {
  summary: string;
  trade_analysis: {
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    avg_win: number;
    avg_loss: number;
    largest_win: number;
    largest_loss: number;
    avg_hold_time: number;
    consecutive_wins: number;
    consecutive_losses: number;
  };
  behavior: {
    revenge_trading: boolean;
    closing_early: boolean;
    fomo_entries: boolean;
    details: string[];
  };
  insight: {
    weakness: string;
    suggestion: string;
  };
};

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

  let analysis: JournalAnalysis | null = null;
  try {
    analysis = await apiPost<JournalAnalysis>("/journal/analyze", { limit: 500 });
  } catch {
    // analysis failed, show only trades
  }

  const totalPnL = trades.reduce((s, t) => s + (t.pnl ?? 0), 0);

  return (
    <Page title="Journal" subtitle={`${trades.length} paper trades registrados — PnL total: ${fmtMoney(totalPnL)}`}>
      {analysis ? (
        <>
          <SectionTitle>AI Analysis</SectionTitle>
          <Panel title={analysis.summary}>
            <div className="stats-grid">
              <Card label="Total trades" value={String(analysis.trade_analysis.total_trades)} />
              <Card label="Win rate" value={`${analysis.trade_analysis.win_rate.toFixed(1)}%`} />
              <Card label="Profit factor" value={analysis.trade_analysis.profit_factor.toFixed(2)} />
              <Card label="Avg win" value={fmtMoney(analysis.trade_analysis.avg_win)} />
              <Card label="Avg loss" value={fmtMoney(analysis.trade_analysis.avg_loss)} />
              <Card label="Largest win" value={fmtMoney(analysis.trade_analysis.largest_win)} />
              <Card label="Largest loss" value={fmtMoney(analysis.trade_analysis.largest_loss)} />
              <Card label="Consecutive wins" value={String(analysis.trade_analysis.consecutive_wins)} />
              <Card label="Consecutive losses" value={String(analysis.trade_analysis.consecutive_losses)} />
              <Card label="Avg hold time" value={`${analysis.trade_analysis.avg_hold_time.toFixed(1)} bars`} />
            </div>

            {analysis.behavior.details.length > 0 ? (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 6, color: "#f59e0b" }}>Behavior flags</div>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {analysis.behavior.details.map((d, i) => (
                    <li key={i} style={{ fontSize: 13, color: "#d97706" }}>{d}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="stats-grid" style={{ marginTop: 12 }}>
              <Card label="Weakness" value={analysis.insight.weakness} />
              <Card label="Suggestion" value={<span style={{ color: "#86efac" }}>{analysis.insight.suggestion}</span>} />
            </div>
          </Panel>
        </>
      ) : null}

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
