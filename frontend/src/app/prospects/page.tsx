import { Page, SectionTitle, thStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { ProspectingActions } from "./prospecting-actions";

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

export default async function ProspectsPage() {
  const ranking = await apiGet<Ranking[]>("/prospecting/ranking");

  return (
    <Page title="Prospects" subtitle="Ranking (GET /prospecting/ranking)" actions={<ProspectingActions />}>
      <SectionTitle>Ranking</SectionTitle>
      <div style={{ marginTop: 8, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={thStyle}>Symbol</th>
              <th style={thStyle}>Reco</th>
              <th style={thStyle}>Score</th>
              <th style={thStyle}>Confluence</th>
              <th style={thStyle}>Price</th>
              <th style={thStyle}>Trend</th>
              <th style={thStyle}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {ranking.map((r) => (
              <tr key={r.symbol} style={{ borderTop: "1px solid #eef2f7" }}>
                <td style={{ padding: 10, fontWeight: 700 }}>{r.symbol}</td>
                <td style={{ padding: 10 }}>{r.recommendation}</td>
                <td style={{ padding: 10 }}>{r.score.toFixed(4)}</td>
                <td style={{ padding: 10 }}>{r.confluence}/3</td>
                <td style={{ padding: 10 }}>{r.price != null ? `$${r.price.toFixed(2)}` : "-"}</td>
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
