import { Card, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { PriceResponse as Price, CandleResponse as Candle } from "@/types";

import { MarketControls } from "./market-controls";

export default async function MarketPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const symbol = typeof params.symbol === "string" ? params.symbol : "BTCUSDT";
  const interval = typeof params.interval === "string" ? params.interval : "1h";
  const limit = typeof params.limit === "string" ? Number(params.limit) : 200;
  const startMs = typeof params.start_ms === "string" ? params.start_ms : "";
  const endMs = typeof params.end_ms === "string" ? params.end_ms : "";
  const desc = params.desc === "true";

  const price = await apiGet<Price>(`/market/price/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}`);
  const candlesQuery = new URLSearchParams({ limit: String(limit) });
  if (startMs) candlesQuery.set("start_ms", startMs);
  if (endMs) candlesQuery.set("end_ms", endMs);
  if (desc) candlesQuery.set("desc", "true");
  const candles = await apiGet<Candle[]>(`/market/candles/${encodeURIComponent(symbol)}/${encodeURIComponent(interval)}?${candlesQuery.toString()}`);

  return (
    <Page title="Market" subtitle="Price + candles (GET /market/*)">
      <MarketControls
        initialSymbol={symbol}
        initialInterval={interval}
        initialLimit={limit}
        initialStartMs={startMs}
        initialEndMs={endMs}
        initialDesc={desc}
      />

      <section className="stats-grid" style={{ marginTop: 14 }}>
        <Card label="Symbol" value={price.symbol} />
        <Card label="Interval" value={price.interval} />
        <Card label="Price" value={`$${price.price.toFixed(2)}`} />
        <Card label="Timestamp" value={new Date(price.ts).toISOString()} />
      </section>

      <SectionTitle>Candles (last {candles.length})</SectionTitle>
      <Panel title="Serie OHLCV reciente">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
                <th style={thStyle}>Open time</th>
                <th style={thStyle}>Open</th>
                <th style={thStyle}>High</th>
                <th style={thStyle}>Low</th>
                <th style={thStyle}>Close</th>
                <th style={thStyle}>Volume</th>
              </tr>
            </thead>
            <tbody>
              {(desc ? candles : candles.slice().reverse()).map((c) => (
                <tr key={c.open_time}>
                  <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{new Date(c.open_time).toISOString()}</td>
                  <td style={tdStyle}>${c.open.toFixed(2)}</td>
                  <td style={tdStyle}>${c.high.toFixed(2)}</td>
                  <td style={tdStyle}>${c.low.toFixed(2)}</td>
                  <td style={{ ...tdStyle, fontWeight: 800 }}>${c.close.toFixed(2)}</td>
                  <td style={tdStyle}>{c.volume.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Panel>
    </Page>
  );
}
