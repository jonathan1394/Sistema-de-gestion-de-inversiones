import { Card, Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { PortfolioPosition, PortfolioTrade } from "@/types";

import { PortfolioActions } from "./portfolio-actions";

type PortfolioState = {
  positions: PortfolioPosition[];
};

type Snapshot = {
  timestamp: string;
  total_value: number;
  cash: number;
  drawdown_pct: number;
};

export default async function PortfolioPage() {
  const state = await apiGet<PortfolioState>("/portfolio/state");
  const trades = await apiGet<PortfolioTrade[]>("/portfolio/trades?limit=100&page=1");
  const snapshots = await apiGet<Snapshot[]>("/portfolio/snapshots?limit=200&page=1");

  const positions = state.positions ?? [];
  const unrealized = positions.reduce((acc, p) => acc + (p.unrealized_pnl ?? 0), 0);
  const lastSnap = snapshots.length ? snapshots[snapshots.length - 1] : null;

  return (
    <Page title="Portfolio" subtitle="Paper portfolio (GET /portfolio/*)" actions={<PortfolioActions />}>
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        <Card label="Positions" value={String(positions.length)} />
        <Card label="Unrealized PnL" value={fmtMoney(unrealized)} />
        <Card label="Last snapshot" value={lastSnap ? fmtMoney(lastSnap.total_value) : "-"} />
        <Card label="Drawdown" value={lastSnap ? `${lastSnap.drawdown_pct.toFixed(2)}%` : "-"} />
      </section>

      <SectionTitle>Positions</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Symbol</th>
              <th style={thStyle}>Qty</th>
              <th style={thStyle}>Entry</th>
              <th style={thStyle}>Current</th>
              <th style={thStyle}>Unrealized</th>
              <th style={thStyle}>Updated</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td style={{ padding: 12, color: "#6b7280" }} colSpan={6}>
                  No hay posiciones.
                </td>
              </tr>
            ) : (
              positions.map((p) => (
                <tr key={p.symbol} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td style={{ padding: 10, fontWeight: 800 }}>{p.symbol}</td>
                  <td style={{ padding: 10 }}>{p.quantity.toFixed(6)}</td>
                  <td style={{ padding: 10 }}>{fmtMoney(p.entry_price)}</td>
                  <td style={{ padding: 10 }}>{fmtMoney(p.current_price)}</td>
                  <td style={{ padding: 10, fontWeight: 800, color: p.unrealized_pnl >= 0 ? "#065f46" : "#b91c1c" }}>
                    {fmtMoney(p.unrealized_pnl)}
                  </td>
                  <td style={{ padding: 10, whiteSpace: "nowrap" }}>{p.updated_at}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <SectionTitle>Trades (last 100)</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Time</th>
              <th style={thStyle}>Symbol</th>
              <th style={thStyle}>Action</th>
              <th style={thStyle}>Qty</th>
              <th style={thStyle}>Price</th>
              <th style={thStyle}>PnL</th>
              <th style={thStyle}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td style={{ padding: 12, color: "#6b7280" }} colSpan={7}>
                  No hay trades.
                </td>
              </tr>
            ) : (
              trades.map((t) => (
                <tr key={t.id} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td style={{ padding: 10, whiteSpace: "nowrap" }}>{t.created_at}</td>
                  <td style={{ padding: 10, fontWeight: 800 }}>{t.symbol}</td>
                  <td style={{ padding: 10, fontWeight: 800 }}>{t.action}</td>
                  <td style={{ padding: 10 }}>{t.quantity.toFixed(6)}</td>
                  <td style={{ padding: 10 }}>{fmtMoney(t.price)}</td>
                  <td style={{ padding: 10, fontWeight: 800, color: t.pnl >= 0 ? "#065f46" : "#b91c1c" }}>
                    {fmtMoney(t.pnl)}
                  </td>
                  <td style={{ padding: 10, color: "#374151" }}>{t.reason}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <SectionTitle>Snapshots (last 200)</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Timestamp</th>
              <th style={thStyle}>Total value</th>
              <th style={thStyle}>Cash</th>
              <th style={thStyle}>Drawdown</th>
            </tr>
          </thead>
          <tbody>
            {snapshots.length === 0 ? (
              <tr>
                <td style={{ padding: 12, color: "#6b7280" }} colSpan={4}>
                  No hay snapshots.
                </td>
              </tr>
            ) : (
              snapshots
                .slice()
                .reverse()
                .map((s, idx) => (
                  <tr key={`${s.timestamp}-${idx}`} style={{ borderTop: "1px solid #eef2f7" }}>
                    <td style={{ padding: 10, whiteSpace: "nowrap" }}>{s.timestamp}</td>
                    <td style={{ padding: 10, fontWeight: 800 }}>{fmtMoney(s.total_value)}</td>
                    <td style={{ padding: 10 }}>{fmtMoney(s.cash)}</td>
                    <td style={{ padding: 10 }}>{s.drawdown_pct.toFixed(2)}%</td>
                  </tr>
                ))
            )}
          </tbody>
        </table>
      </div>
    </Page>
  );
}

function fmtMoney(v: number): string {
  if (!Number.isFinite(v)) return "-";
  return `$${v.toFixed(2)}`;
}
