import { Badge, Card, Page, Panel, SectionTitle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { DataHealthRow, InvestmentReview } from "@/types";

import { ReviewActions } from "./review-actions";

function statusTone(status: string): "info" | "success" | "warning" | "danger" {
  if (status === "investable" || status === "ok") return "success";
  if (status === "review_required" || status === "short_history") return "warning";
  if (status === "stale" || status === "gaps_detected" || status === "missing") return "danger";
  return "info";
}

export default async function InvestmentReviewPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const symbol = typeof params.symbol === "string" ? params.symbol : "BTCUSDT";
  const interval = typeof params.interval === "string" ? params.interval : "1d";
  const backtestInterval = typeof params.backtest_interval === "string" ? params.backtest_interval : "4h";
  const amount = typeof params.amount === "string" ? params.amount : "50";
  const review = await apiGet<InvestmentReview>(
    `/evaluation/investment/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}&backtest_interval=${encodeURIComponent(backtestInterval)}&amount=${encodeURIComponent(amount)}`,
  );
  const passedChecks = Object.values(review.protocol.checks).filter(Boolean).length;
  const totalChecks = Object.keys(review.protocol.checks).length;
  const healthiestRow = review.data_health.find((row) => row.status === "ok") ?? review.data_health[0];
  const bestRow = review.backtest.strategies.find((row) => row.strategy_name === review.backtest.best_strategy) ?? review.backtest.strategies[0];

  return (
    <Page
      title="Investment Review"
      subtitle="Protocolo oficial: datos -> ranking -> backtest -> riesgo -> decision"
      actions={<Badge tone={statusTone(review.protocol.status)}>{review.protocol.status}</Badge>}
    >
      <form className="panel" style={{ padding: 16 }} method="GET" action="/investment-review">
        <div className="field-grid">
          <label className="field">
            <span className="field-label">Symbol</span>
            <input name="symbol" defaultValue={symbol} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Prospecting interval</span>
            <input name="interval" defaultValue={interval} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Backtest interval</span>
            <input name="backtest_interval" defaultValue={backtestInterval} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Amount (USDT)</span>
            <input name="amount" defaultValue={amount} className="input" />
          </label>
        </div>
        <div className="button-row" style={{ marginTop: 14 }}>
          <button className="button-primary" type="submit">Run review</button>
        </div>
      </form>

      <ReviewActions
        initialSymbol={symbol}
        initialInterval={interval}
        initialAmount={amount}
        symbolConfigured={review.universe.symbol_configured}
      />

      <section className="review-banner" style={{ marginTop: 14 }}>
        <div>
          <div className="review-banner-label">Executive read</div>
          <div className="review-banner-title">
            {review.protocol.status === "investable" ? "Candidate ready for capital review" : "Candidate still needs validation"}
          </div>
          <p className="review-banner-text">
            {review.risk?.reason ?? review.backtest.reason ?? "No consolidated reason available yet."}
          </p>
        </div>
        <div className="review-banner-pills">
          <Badge tone={statusTone(review.protocol.status)}>{review.protocol.status}</Badge>
          <Badge tone={review.universe.symbol_configured ? "success" : "danger"}>{review.universe.symbol_configured ? "In universe" : "Out of universe"}</Badge>
          <Badge tone={review.risk?.approved ? "success" : "warning"}>{review.risk?.approved ? "Risk approved" : "Risk review"}</Badge>
        </div>
      </section>

      <section className="stats-grid" style={{ marginTop: 14 }}>
        <Card label="Universe" value={review.universe.symbol_configured ? "Configured" : "Out of scope"} />
        <Card label="Recommendation" value={review.ranking?.recommendation ?? "No prospect"} />
        <Card label="Best strategy" value={review.backtest.best_strategy ?? "N/A"} />
        <Card label="Risk" value={<Badge tone={review.risk?.approved ? "success" : "danger"}>{review.risk?.approved ? "Approved" : "Blocked"}</Badge>} />
        <Card label="Checks passed" value={`${passedChecks}/${totalChecks}`} />
        <Card label="Freshest timeframe" value={healthiestRow?.interval ?? "-"} />
        <Card label="Backtest PF" value={bestRow ? bestRow.metrics.profit_factor : "-"} />
        <Card label="Current price" value={review.risk?.current_price != null ? `$${review.risk.current_price.toFixed(2)}` : "-"} />
      </section>

      <SectionTitle>Protocol checks</SectionTitle>
      <Panel title="Criterios minimos para pasar de evaluacion a candidatura invertible">
        <div className="stats-grid">
          {Object.entries(review.protocol.checks).map(([key, passed]) => (
            <Card key={key} label={key.replaceAll("_", " ")} value={<Badge tone={passed ? "success" : "danger"}>{passed ? "OK" : "Blocked"}</Badge>} />
          ))}
        </div>
        <div className="review-thresholds">
          <div className="review-threshold">
            <span className="review-threshold-label">Min trades</span>
            <strong>{review.protocol.min_trades}</strong>
          </div>
          <div className="review-threshold">
            <span className="review-threshold-label">Min PF</span>
            <strong>{review.protocol.min_profit_factor}</strong>
          </div>
          <div className="review-threshold">
            <span className="review-threshold-label">Min Sharpe</span>
            <strong>{review.protocol.min_sharpe_ratio}</strong>
          </div>
          <div className="review-threshold">
            <span className="review-threshold-label">Score threshold</span>
            <strong>{review.protocol.investing_score_threshold}</strong>
          </div>
          <div className="review-threshold">
            <span className="review-threshold-label">Min confluence</span>
            <strong>{review.protocol.min_confluence_for_invest}</strong>
          </div>
        </div>
      </Panel>

      <SectionTitle>Data health</SectionTitle>
      <Panel title="Frescura, continuidad y suficiente historia por timeframe">
        <DataHealthTable rows={review.data_health} />
      </Panel>

      <SectionTitle>Decision context</SectionTitle>
      <Panel title="Prospect score, confluencia y evaluacion de riesgo">
        <div className="stats-grid">
          <Card label="Score" value={review.ranking?.score?.toFixed(4) ?? "-"} />
          <Card label="Confluence" value={review.ranking != null ? `${review.ranking.confluence}/3` : "-"} />
          <Card label="Trend" value={review.prospect?.trend ?? "-"} />
          <Card label="Prospect status" value={review.prospect?.status ?? "No prospect"} />
          <Card label="Signals" value={review.prospect?.signals_count ?? "-"} />
          <Card label="Suggested qty" value={review.risk?.quantity != null ? review.risk.quantity.toFixed(6) : "-"} />
          <Card label="Risk reason" value={review.risk?.reason ?? "No risk evaluation"} />
        </div>
      </Panel>

      <SectionTitle>Backtest compare</SectionTitle>
      <Panel title="Comparativa resumida de estrategias sobre el activo">
        {!review.backtest.ready && review.backtest.reason ? (
          <p style={{ color: "var(--muted)", padding: 16 }}>{review.backtest.reason}</p>
        ) : (
          <TableWrap>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={thStyle}>Strategy</th>
                  <th style={thStyle}>Passed</th>
                  <th style={thStyle}>Trades</th>
                  <th style={thStyle}>Profit factor</th>
                  <th style={thStyle}>Sharpe</th>
                  <th style={thStyle}>Max DD</th>
                  <th style={thStyle}>ROI</th>
                </tr>
              </thead>
              <tbody>
                {review.backtest.strategies.map((row) => (
                  <tr key={row.strategy_name}>
                    <td style={{ ...tdStyle, fontWeight: 800 }}>{row.strategy_name}</td>
                    <td style={tdStyle}><Badge tone={row.passed_validation ? "success" : "warning"}>{String(row.passed_validation)}</Badge></td>
                    <td style={tdStyle}>{row.metrics.total_trades}</td>
                    <td style={tdStyle}>{row.metrics.profit_factor}</td>
                    <td style={tdStyle}>{row.metrics.sharpe_ratio}</td>
                    <td style={tdStyle}>{row.metrics.max_drawdown_pct}%</td>
                    <td style={tdStyle}>{row.metrics.roi_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Panel>
    </Page>
  );
}

function DataHealthTable({ rows }: { rows: DataHealthRow[] }) {
  return (
    <TableWrap>
      <table className="data-table">
        <thead>
          <tr>
            <th style={thStyle}>Interval</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>Candles</th>
            <th style={thStyle}>Age min</th>
            <th style={thStyle}>Price</th>
            <th style={thStyle}>Validation</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.symbol}-${row.interval}`}>
              <td style={{ ...tdStyle, fontWeight: 800 }}>{row.interval}</td>
              <td style={tdStyle}><Badge tone={statusTone(row.status)}>{row.status}</Badge></td>
              <td style={tdStyle}>{row.count}</td>
              <td style={tdStyle}>{row.age_minutes ?? "-"}</td>
              <td style={tdStyle}>{row.latest_price != null ? `$${row.latest_price.toFixed(2)}` : "-"}</td>
              <td style={{ ...tdStyle, color: "var(--muted)" }}>{row.validation_errors[0] ?? "OK"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}
