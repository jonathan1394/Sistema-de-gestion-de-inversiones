import { Card, Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

type Config = {
  mode: string;
  kill_switch: boolean;
};

type MarketPrice = { symbol: string; interval: string; price: number; ts: number };

export default async function OverviewPage() {
  const cfg = await apiGet<Config>("/config");
  const prices = await apiGet<MarketPrice[]>("/market/summary?symbols=BTCUSDT,ETHUSDT,SOLUSDT&interval=1h");

  return (
    <Page title="Overview" subtitle="Config + market summary">
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
        <Card label="App mode" value={String(cfg?.mode ?? "-")} />
        <Card label="Kill switch" value={String(cfg?.kill_switch ?? "-")} />
      </section>

      <SectionTitle>Market Summary</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Symbol</th>
              <th style={thStyle}>Interval</th>
              <th style={thStyle}>Price</th>
              <th style={thStyle}>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {prices.map((p) => (
              <tr key={p.symbol} style={{ borderTop: "1px solid #eef2f7" }}>
                <td style={{ padding: 10, fontWeight: 650 }}>{p.symbol}</td>
                <td style={{ padding: 10 }}>{p.interval}</td>
                <td style={{ padding: 10 }}>${p.price.toFixed(2)}</td>
                <td style={{ padding: 10 }}>{new Date(p.ts).toISOString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
