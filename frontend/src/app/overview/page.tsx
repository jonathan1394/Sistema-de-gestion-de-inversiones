import { Badge, Card, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { Config, PriceResponse as MarketPrice, SystemStatus } from "@/types";

export default async function OverviewPage() {
  const cfg = await apiGet<Config>("/config");
  const prices = await apiGet<MarketPrice[]>("/market/summary?symbols=BTCUSDT,ETHUSDT,SOLUSDT&interval=1h");
  const systemStatus = await apiGet<SystemStatus>("/system/status");

  return (
    <Page title="Overview" subtitle="Config + market summary">
      <section className="stats-grid">
        <Card label="App mode" value={String(cfg?.mode ?? "-")} />
        <Card label="Kill switch" value={<Badge tone={cfg?.kill_switch ? "danger" : "success"}>{String(cfg?.kill_switch ?? "-")}</Badge>} />
        <Card label="Server time" value={systemStatus?.timestamp ? new Date(systemStatus.timestamp).toLocaleString() : "-"} />
        <Card label="Trading mode" value={cfg?.trading?.mode ?? "-"} />
      </section>

      <SectionTitle>Operational config</SectionTitle>
      <Panel title="Resumen expandido de configuración pública">
        <div className="stats-grid">
          <Card label="Initial capital" value={cfg.capital ? `$${cfg.capital.initial_usdt.toFixed(2)}` : "-"} />
          <Card label="Trading fee" value={cfg.fees ? `${(cfg.fees.trading_fee_pct * 100).toFixed(2)}%` : "-"} />
          <Card label="Slippage" value={cfg.fees ? `${(cfg.fees.slippage_pct * 100).toFixed(2)}%` : "-"} />
          <Card label="Stop loss required" value={<Badge tone={cfg.risk?.require_stop_loss ? "warning" : "info"}>{String(cfg.risk?.require_stop_loss ?? false)}</Badge>} />
        </div>

        <details style={{ marginTop: 14 }}>
          <summary style={{ cursor: "pointer", fontWeight: 800 }}>Risk settings</summary>
          <div className="stats-grid" style={{ marginTop: 12 }}>
            <Card label="Max position" value={cfg.risk ? `${(cfg.risk.max_position_size_pct * 100).toFixed(2)}%` : "-"} />
            <Card label="Risk per trade" value={cfg.risk ? `${(cfg.risk.max_risk_per_trade_pct * 100).toFixed(2)}%` : "-"} />
            <Card label="Max exposure" value={cfg.risk ? `${(cfg.risk.max_total_exposure_pct * 100).toFixed(2)}%` : "-"} />
            <Card label="Default stop" value={cfg.risk ? `${(cfg.risk.default_stop_loss_pct * 100).toFixed(2)}%` : "-"} />
          </div>
        </details>

        <details style={{ marginTop: 14 }}>
          <summary style={{ cursor: "pointer", fontWeight: 800 }}>Trading and timeframes</summary>
          <div className="stats-grid" style={{ marginTop: 12 }}>
            <Card label="Real trading" value={String(cfg.trading?.allow_real_trading ?? false)} />
            <Card label="Futures" value={String(cfg.trading?.allow_futures ?? false)} />
            <Card label="Leverage" value={String(cfg.trading?.allow_leverage ?? false)} />
            <Card label="Timeframes" value={cfg.timeframes?.join(", ") ?? "-"} />
          </div>
        </details>
      </Panel>

      <SectionTitle>Market Summary</SectionTitle>
      <Panel title="Activos consultados desde la API">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
                <th style={thStyle}>Symbol</th>
                <th style={thStyle}>Interval</th>
                <th style={thStyle}>Price</th>
                <th style={thStyle}>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {prices.map((p) => (
                <tr key={p.symbol}>
                  <td style={{ ...tdStyle, fontWeight: 700 }}>{p.symbol}</td>
                  <td style={tdStyle}>{p.interval}</td>
                  <td style={{ ...tdStyle, fontWeight: 800 }}>${p.price.toFixed(2)}</td>
                  <td style={tdStyle}>{new Date(p.ts).toISOString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Panel>
    </Page>
  );
}
