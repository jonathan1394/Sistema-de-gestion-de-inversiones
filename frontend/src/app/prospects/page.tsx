import { Badge, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { ProspectingActions } from "./prospecting-actions";
import { ProspectingFilters } from "./prospecting-filters";
import { ProspectsList } from "./prospects-list";

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

export default async function ProspectsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const status = typeof params.status === "string" ? params.status : "";
  const minScore = typeof params.min_score === "string" ? params.min_score : "";
  const ranking = await apiGet<Ranking[]>("/prospecting/ranking");
  const prospectsQuery = new URLSearchParams({ page: "1", limit: "50" });
  if (status) prospectsQuery.set("status", status);
  if (minScore) prospectsQuery.set("min_score", minScore);
  const prospects = await apiGet<ProspectRow[]>(`/prospecting/prospects?${prospectsQuery.toString()}`);

  return (
    <Page title="Prospects" subtitle="Ranking (GET /prospecting/ranking)" actions={<ProspectingActions />}>
      <SectionTitle>Filters</SectionTitle>
      <ProspectingFilters initialStatus={status} initialMinScore={minScore} />

      <SectionTitle>Persistent prospects</SectionTitle>
      <Panel title="Watchlist persistida y accionable">
        <ProspectsList prospects={prospects} />
      </Panel>

      <SectionTitle>Ranking</SectionTitle>
      <Panel title="Activos priorizados por score y confluencia">
        <TableWrap>
          <table className="data-table">
            <thead>
              <tr>
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
                <tr key={r.symbol}>
                  <td style={{ ...tdStyle, fontWeight: 700 }}>{r.symbol}</td>
                  <td style={tdStyle}><RecoBadge value={r.recommendation} /></td>
                  <td style={{ ...tdStyle, fontWeight: 800 }}>{r.score.toFixed(4)}</td>
                  <td style={tdStyle}>{r.confluence}/3</td>
                  <td style={tdStyle}>{r.price != null ? `$${r.price.toFixed(2)}` : "-"}</td>
                  <td style={tdStyle}>{[r.trend_1h, r.trend_4h, r.trend_1d].filter(Boolean).join(" / ")}</td>
                  <td style={{ ...tdStyle, color: "var(--muted)" }}>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Panel>
    </Page>
  );
}

type ProspectRow = {
  symbol: string;
  interval: string;
  status: string;
  score: number;
  trend?: string | null;
  volatility?: string | null;
  volume_profile?: string | null;
  rsi_condition?: string | null;
  signals_count: number;
  notes: string;
};

function RecoBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  if (normalized.includes("invert")) return <Badge tone="success">{value}</Badge>;
  if (normalized.includes("vigil")) return <Badge tone="warning">{value}</Badge>;
  if (normalized.includes("evit")) return <Badge tone="danger">{value}</Badge>;
  return <Badge tone="info">{value}</Badge>;
}
