import Link from "next/link";

import { Page, Card, SectionTitle, preStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { PriceResponse, CandleResponse, Ranking } from "@/types";

function trendColor(v: string | null | undefined): string {
  if (!v) return "#6b7280";
  if (v === "up" || v === "bullish") return "#059669";
  if (v === "down" || v === "bearish") return "#b91c1c";
  return "#6b7280";
}

function fmtPct(v: number | null | undefined): string {
  return v == null ? "-" : `${(v * 100).toFixed(2)}%`;
}

type Props = {
  params: Promise<{ symbol: string }>;
};

export default async function AssetDetailPage({ params }: Props) {
  const { symbol } = await params;
  const sym = symbol.toUpperCase();

  const [priceData, decisionData, candles] = await Promise.all([
    apiGet<PriceResponse>(`/market/price/${sym}`).catch(() => null),
    apiGet<Ranking>(`/prospecting/decision/${sym}`).catch(() => null),
    apiGet<CandleResponse[]>(`/market/candles/${sym}/1h?limit=100`).catch(() => []),
  ]);

  const price = priceData?.price ?? decisionData?.price ?? candles[candles.length - 1]?.close ?? null;
  const candleHi = candles.length ? Math.max(...candles.map((c) => c.high)) : 0;
  const candleLo = candles.length ? Math.min(...candles.map((c) => c.low)) : 0;
  const range = candleHi - candleLo || 1;
  const chartHeight = 120;

  return (
    <Page title={sym} subtitle={`Asset detail — ${price != null ? `$${price.toFixed(2)}` : "no price"}`}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <Card label="Price" value={price != null ? `$${price.toFixed(2)}` : "—"} />
        <Card label="Score" value={decisionData?.score?.toFixed(4) ?? "—"} />
        <Card label="Confluence" value={decisionData?.confluence != null ? `${decisionData.confluence}/3` : "—"} />
        <Card label="Recommendation" value={decisionData?.recommendation ?? "—"} />
      </div>

      {decisionData && (
        <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>
            Reason: <span style={{ color: "#111827", fontWeight: 600 }}>{decisionData.reason}</span>
          </div>
          {[decisionData.trend_1h, decisionData.trend_4h, decisionData.trend_1d].some(Boolean) && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {decisionData.trend_1h && (
                <span style={{ color: trendColor(decisionData.trend_1h), fontWeight: 700, fontSize: 12 }}>
                  1h:{decisionData.trend_1h}
                </span>
              )}
              {decisionData.trend_4h && (
                <span style={{ color: trendColor(decisionData.trend_4h), fontWeight: 700, fontSize: 12 }}>
                  4h:{decisionData.trend_4h}
                </span>
              )}
              {decisionData.trend_1d && (
                <span style={{ color: trendColor(decisionData.trend_1d), fontWeight: 700, fontSize: 12 }}>
                  1d:{decisionData.trend_1d}
                </span>
              )}
            </div>
          )}
          {decisionData.return_pct_1d != null && (
            <span style={{ color: decisionData.return_pct_1d >= 0 ? "#059669" : "#b91c1c", fontWeight: 700, fontSize: 12 }}>
              1d: {decisionData.return_pct_1d >= 0 ? "+" : ""}{decisionData.return_pct_1d.toFixed(2)}%
            </span>
          )}
        </div>
      )}

      {candles.length >= 2 && (
        <>
          <SectionTitle>Price action (1h, last {candles.length} candles)</SectionTitle>
          <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, padding: 12 }}>
            <svg viewBox={`0 0 ${candles.length * 6} ${chartHeight}`} style={{ width: "100%", height: chartHeight }}>
              {candles.map((c, i) => {
                const x = i * 6 + 2;
                const isUp = c.close >= c.open;
                const yOpen = chartHeight - ((c.open - candleLo) / range) * chartHeight;
                const yClose = chartHeight - ((c.close - candleLo) / range) * chartHeight;
                const yHigh = chartHeight - ((c.high - candleLo) / range) * chartHeight;
                const yLow = chartHeight - ((c.low - candleLo) / range) * chartHeight;
                const bodyTop = Math.min(yOpen, yClose);
                const bodyH = Math.max(Math.abs(yClose - yOpen), 1);
                return (
                  <g key={c.open_time}>
                    <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={isUp ? "#059669" : "#b91c1c"} strokeWidth={1} />
                    <rect x={x - 2} y={bodyTop} width={4} height={bodyH} fill={isUp ? "#059669" : "#b91c1c"} rx={1} />
                  </g>
                );
              })}
            </svg>
          </div>
        </>
      )}

      <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link
          href={`/backtest?symbol=${sym}`}
          style={{ border: "1px solid #111827", borderRadius: 10, padding: "8px 16px", fontWeight: 700, background: "#111827", color: "white", textDecoration: "none" }}
        >
          Backtest {sym}
        </Link>
        <Link
          href={`/risk?symbol=${sym}`}
          style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: "8px 16px", fontWeight: 700, background: "white", color: "#111827", textDecoration: "none" }}
        >
          Risk evaluate
        </Link>
      </div>
    </Page>
  );
}
