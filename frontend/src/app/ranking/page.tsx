import Link from "next/link";

import { Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

type Ranking = {
  symbol: string;
  score: number;
  confluence: number;
  recommendation: string;
  reason: string;
  trend_1h?: string | null;
  trend_4h?: string | null;
  trend_1d?: string | null;
  price?: number | null;
  return_pct_1d?: number | null;
};

function formatPct(value?: number | null) {
  return value == null ? "-" : `${value.toFixed(2)}%`;
}

export default async function RankingPage() {
  const ranking = await apiGet<Ranking[]>("/prospecting/ranking");

  return (
    <Page title="Ranking" subtitle="Prospecting ranking ordenado por score (GET /prospecting/ranking)">
      <SectionTitle>Mejores candidatos</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Rank</th>
              <th style={thStyle}>Symbol</th>
              <th style={thStyle}>Reco</th>
              <th style={thStyle}>Score</th>
              <th style={thStyle}>Confluence</th>
              <th style={thStyle}>Price</th>
              <th style={thStyle}>1d</th>
              <th style={thStyle}>Trend</th>
              <th style={thStyle}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {ranking.map((r, index) => (
              <tr key={r.symbol} style={{ borderTop: "1px solid #eef2f7" }}>
                <td style={{ padding: 10, color: "#6b7280", fontWeight: 700 }}>{index + 1}</td>
                <td style={{ padding: 10, fontWeight: 800 }}>
                  <Link href={`/assets/${encodeURIComponent(r.symbol)}`} style={{ color: "#111827" }}>
                    {r.symbol}
                  </Link>
                </td>
                <td style={{ padding: 10 }}>{r.recommendation}</td>
                <td style={{ padding: 10 }}>{r.score.toFixed(4)}</td>
                <td style={{ padding: 10 }}>{r.confluence}/3</td>
                <td style={{ padding: 10 }}>{r.price != null ? `$${r.price.toFixed(2)}` : "-"}</td>
                <td style={{ padding: 10 }}>{formatPct(r.return_pct_1d)}</td>
                <td style={{ padding: 10 }}>{[r.trend_1h, r.trend_4h, r.trend_1d].filter(Boolean).join(" / ")}</td>
                <td style={{ padding: 10, color: "#374151" }}>{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
