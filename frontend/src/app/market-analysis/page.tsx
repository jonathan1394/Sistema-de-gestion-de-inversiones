import { Badge, Card, Page, Panel, SectionTitle, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

type TFEntry = {
  interval: string;
  price: number;
  return_pct: number;
  trend: string;
  volatility: string;
  rsi: string;
  volume: string;
  summary_text: string;
  key_levels: Record<string, number>;
  volatility_pct: number;
};

type Analysis = {
  symbol: string;
  timeframes: TFEntry[];
  confluence: number;
  total_timeframes: number;
};

function TrendBadge({ trend }: { trend: string }) {
  const tone = trend.includes("up") ? "success" : trend.includes("down") ? "danger" : "warning";
  return <Badge tone={tone as "success" | "danger" | "warning"}>{trend}</Badge>;
}

function RsiBadge({ rsi }: { rsi: string }) {
  const tone = rsi === "oversold" ? "success" : rsi === "overbought" ? "danger" : "info";
  return <Badge tone={tone as "success" | "danger" | "info"}>{rsi}</Badge>;
}

function VolatilityBadge({ vol }: { vol: string }) {
  const tone = vol === "high" ? "danger" : vol === "low" ? "success" : "info";
  return <Badge tone={tone as "success" | "danger" | "info"}>{vol}</Badge>;
}

export default async function MarketAnalysisPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const symbol = typeof params.symbol === "string" ? params.symbol : "BTCUSDT";
  const intervals = typeof params.intervals === "string" ? params.intervals : "1h,4h,1d";

  let analysis: Analysis | null = null;
  let error: string | null = null;
  try {
    analysis = await apiGet<Analysis>(`/market/analysis/${encodeURIComponent(symbol)}?intervals=${encodeURIComponent(intervals)}`);
  } catch (e) {
    error = String(e);
  }

  return (
    <Page title="Market Analysis" subtitle="Multi-timeframe confluence analysis">
      <form className="panel" style={{ padding: 16, marginBottom: 14 }} method="GET" action="/market-analysis">
        <div className="field-grid">
          <label className="field">
            <span className="field-label">Symbol</span>
            <input name="symbol" defaultValue={symbol} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Intervals</span>
            <input name="intervals" defaultValue={intervals} className="input" placeholder="1h,4h,1d" />
          </label>
        </div>
        <div className="button-row" style={{ marginTop: 14 }}>
          <button className="button-primary" type="submit">Analyze</button>
        </div>
      </form>

      {error ? (
        <p style={{ color: "#fca5a5" }}>Error: {error}</p>
      ) : analysis ? (
        <>
          <section className="stats-grid">
            <Card label="Symbol" value={<span style={{ fontWeight: 800 }}>{analysis.symbol}</span>} />
            <Card label="Confluence" value={
              <Badge tone={analysis.confluence >= 2 ? "success" : analysis.confluence >= 1 ? "warning" : "danger"}>
                {analysis.confluence}/{analysis.total_timeframes}
              </Badge>
            } />
            <Card label="Timeframes" value={String(analysis.total_timeframes)} />
          </section>

          <SectionTitle>Timeframe Analysis</SectionTitle>

          {analysis.timeframes.map((tf) => (
            <Panel key={tf.interval} title={`${tf.interval} — ${tf.summary_text}`}>
              <div className="stats-grid" style={{ marginBottom: 12 }}>
                <Card label="Price" value={`$${tf.price.toFixed(2)}`} />
                <Card label="Return" value={fmtPct(tf.return_pct)} />
                <Card label="Trend" value={<TrendBadge trend={tf.trend} />} />
                <Card label="RSI" value={<RsiBadge rsi={tf.rsi} />} />
                <Card label="Volatility" value={<VolatilityBadge vol={tf.volatility} />} />
                <Card label="Volume" value={tf.volume} />
                <Card label="Volatility %" value={`${tf.volatility_pct.toFixed(2)}%`} />
              </div>

              <details>
                <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
                  Key levels
                </summary>
                <table className="data-table" style={{ fontSize: 12, width: "auto" }}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Level</th>
                      <th style={thStyle}>Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(tf.key_levels).map(([level, price]) => (
                      <tr key={level}>
                        <td style={{ ...tdStyle, fontWeight: 700 }}>{level}</td>
                        <td style={tdStyle}>${price.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </Panel>
          ))}
        </>
      ) : (
        <p style={{ color: "var(--muted)" }}>Enter a symbol and click Analyze.</p>
      )}
    </Page>
  );
}

function fmtPct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}
