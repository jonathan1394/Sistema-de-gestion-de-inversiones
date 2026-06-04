import { Card, Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { PriceResponse as Price, CandleResponse as Candle } from "@/types";

import { MarketControls } from "./market-controls";

export default async function MarketPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>;
}) {
  const symbol = typeof searchParams?.symbol === "string" ? searchParams.symbol : "BTCUSDT";
  const interval = typeof searchParams?.interval === "string" ? searchParams.interval : "1h";
  const limit = typeof searchParams?.limit === "string" ? Number(searchParams.limit) : 200;

  const price = await apiGet<Price>(`/market/price/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}`);
  const candles = await apiGet<Candle[]>(
    `/market/candles/${encodeURIComponent(symbol)}/${encodeURIComponent(interval)}?limit=${encodeURIComponent(
      String(limit)
    )}`
  );

  return (
    <Page title="Market" subtitle="Price + candles (GET /market/*)">
      <MarketControls initialSymbol={symbol} initialInterval={interval} initialLimit={limit} />

      <section
        style={{
          marginTop: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        <Card label="Symbol" value={price.symbol} />
        <Card label="Interval" value={price.interval} />
        <Card label="Price" value={`$${price.price.toFixed(2)}`} />
        <Card label="Timestamp" value={new Date(price.ts).toISOString()} />
      </section>

      <SectionTitle>Candles (last {candles.length})</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Open time</th>
              <th style={thStyle}>Open</th>
              <th style={thStyle}>High</th>
              <th style={thStyle}>Low</th>
              <th style={thStyle}>Close</th>
              <th style={thStyle}>Volume</th>
            </tr>
          </thead>
          <tbody>
            {candles
              .slice()
              .reverse()
              .map((c) => (
                <tr key={c.open_time} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td style={{ padding: 10, whiteSpace: "nowrap" }}>{new Date(c.open_time).toISOString()}</td>
                  <td style={{ padding: 10 }}>${c.open.toFixed(2)}</td>
                  <td style={{ padding: 10 }}>${c.high.toFixed(2)}</td>
                  <td style={{ padding: 10 }}>${c.low.toFixed(2)}</td>
                  <td style={{ padding: 10, fontWeight: 800 }}>${c.close.toFixed(2)}</td>
                  <td style={{ padding: 10 }}>{c.volume.toFixed(2)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
