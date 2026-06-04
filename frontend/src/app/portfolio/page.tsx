import { Card, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
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

export default async function PortfolioPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const page = typeof params.page === "string" ? Math.max(1, Number(params.page) || 1) : 1;
  const symbol = typeof params.symbol === "string" ? params.symbol : "";
  const state = await apiGet<PortfolioState>("/portfolio/state");
  const tradesQuery = new URLSearchParams({ limit: "100", page: String(page) });
  if (symbol) tradesQuery.set("symbol", symbol);
  const trades = await apiGet<PortfolioTrade[]>(`/portfolio/trades?${tradesQuery.toString()}`);
  const snapshots = await apiGet<Snapshot[]>("/portfolio/snapshots?limit=200&page=1");

  const positions = state.positions ?? [];
  const unrealized = positions.reduce((acc, p) => acc + (p.unrealized_pnl ?? 0), 0);
  const lastSnap = snapshots.length ? snapshots[snapshots.length - 1] : null;

  return (
    <Page
      title="Portfolio"
      subtitle="Paper portfolio (GET /portfolio/*)"
      actions={<PortfolioActions initialSymbol={symbol} initialPage={page} />}
    >
      <section className="stats-grid">
        <Card label="Positions" value={String(positions.length)} />
        <Card label="Unrealized PnL" value={fmtMoney(unrealized)} />
        <Card label="Last snapshot" value={lastSnap ? fmtMoney(lastSnap.total_value) : "-"} />
        <Card label="Drawdown" value={lastSnap ? `${lastSnap.drawdown_pct.toFixed(2)}%` : "-"} />
      </section>

      <SectionTitle>Positions</SectionTitle>
      <Panel title="Posiciones abiertas">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
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
                  <td className="empty-state" colSpan={6}>
                    No hay posiciones.
                  </td>
                </tr>
              ) : (
                positions.map((p) => (
                  <tr key={p.symbol}>
                    <td style={{ ...tdStyle, fontWeight: 800 }}>{p.symbol}</td>
                    <td style={tdStyle}>{p.quantity.toFixed(6)}</td>
                    <td style={tdStyle}>{fmtMoney(p.entry_price)}</td>
                    <td style={tdStyle}>{fmtMoney(p.current_price)}</td>
                    <td style={{ ...tdStyle, fontWeight: 800, color: p.unrealized_pnl >= 0 ? "#86efac" : "#fca5a5" }}>
                      {fmtMoney(p.unrealized_pnl)}
                    </td>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{p.updated_at}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </TableWrap>
      </Panel>

      <SectionTitle>Trades (last 100)</SectionTitle>
      <Panel title="Historial reciente de operaciones">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
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
                  <td className="empty-state" colSpan={7}>
                    No hay trades.
                  </td>
                </tr>
              ) : (
                trades.map((t) => (
                  <tr key={t.id}>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{t.created_at}</td>
                    <td style={{ ...tdStyle, fontWeight: 800 }}>{t.symbol}</td>
                    <td style={{ ...tdStyle, fontWeight: 800 }}>{t.action}</td>
                    <td style={tdStyle}>{t.quantity.toFixed(6)}</td>
                    <td style={tdStyle}>{fmtMoney(t.price)}</td>
                    <td style={{ ...tdStyle, fontWeight: 800, color: t.pnl >= 0 ? "#86efac" : "#fca5a5" }}>
                      {fmtMoney(t.pnl)}
                    </td>
                    <td style={{ ...tdStyle, color: "var(--muted)" }}>{t.reason}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </TableWrap>
      </Panel>

      <SectionTitle>Snapshots (last 200)</SectionTitle>
      <Panel title="Evolución del portfolio">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
                <th style={thStyle}>Timestamp</th>
                <th style={thStyle}>Total value</th>
                <th style={thStyle}>Cash</th>
                <th style={thStyle}>Drawdown</th>
              </tr>
            </thead>
            <tbody>
              {snapshots.length === 0 ? (
                <tr>
                  <td className="empty-state" colSpan={4}>
                    No hay snapshots.
                  </td>
                </tr>
              ) : (
                snapshots
                  .slice()
                  .reverse()
                  .map((s, idx) => (
                    <tr key={`${s.timestamp}-${idx}`}>
                      <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{s.timestamp}</td>
                      <td style={{ ...tdStyle, fontWeight: 800 }}>{fmtMoney(s.total_value)}</td>
                      <td style={tdStyle}>{fmtMoney(s.cash)}</td>
                      <td style={tdStyle}>{s.drawdown_pct.toFixed(2)}%</td>
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

function fmtMoney(v: number): string {
  if (!Number.isFinite(v)) return "-";
  return `$${v.toFixed(2)}`;
}
