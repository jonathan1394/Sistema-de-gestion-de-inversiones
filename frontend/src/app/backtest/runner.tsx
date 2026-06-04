"use client";

import { useMemo, useState, useTransition } from "react";

import { Badge, Card, Panel, SectionTitle, preStyle, TableWrap, thStyle, tdStyle } from "@/app/components/ui";
import { apiPost } from "@/lib/api";

type Strategy = { id: string; label: string };

type Props = {
  strategies: Strategy[];
  initialSymbol: string;
};

type BacktestResponse = {
  result: {
    symbol: string;
    interval: string;
    initial_capital: number;
    final_capital: number;
    total_fees: number;
    strategy_name: string;
    parameters: Record<string, unknown>;
  };
  metrics: Record<string, unknown>;
  trades: Array<Record<string, unknown>>;
  equity_curve: Array<{ timestamp: string; equity: number }>;
};

type CompareResponse = {
  symbol: string;
  interval: string;
  initial_capital: number;
  best_strategy: string | null;
  strategies: Array<{
    strategy_name: string;
    passed_validation: boolean;
    metrics: Record<string, number | string>;
  }>;
};

export function BacktestRunner({ strategies, initialSymbol }: Props) {
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [interval, setInterval] = useState("1h");
  const [capital, setCapital] = useState("1000");
  const [limit, setLimit] = useState("1000");
  const [strategy, setStrategy] = useState(strategies[0]?.id ?? "ma");
  const [paramsJson, setParamsJson] = useState("{}");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BacktestResponse | null>(null);
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [comparePending, setComparePending] = useState(false);

  const strategyOptions = useMemo(() => strategies, [strategies]);

  async function run() {
    setError(null);
    setData(null);
    setCompareData(null);

    let params: Record<string, unknown> = {};
    try {
      params = paramsJson.trim() ? JSON.parse(paramsJson) : {};
    } catch {
      setError("params JSON inválido");
      return;
    }

    const payload = {
      symbol: symbol.trim().toUpperCase(),
      interval: interval.trim(),
      strategy,
      capital: Number(capital),
      limit: Number(limit),
      params,
    };

    try {
      const data = await apiPost<BacktestResponse>("/backtest/run", payload);
      setData(data);
    } catch (e) {
      setError(String(e));
    }
  }

  async function runCompare() {
    setError(null);
    setData(null);
    setCompareData(null);
    setComparePending(true);
    try {
      const data = await apiPost<CompareResponse>("/backtest/compare", {
        symbol: symbol.trim().toUpperCase(),
        interval: interval.trim(),
        capital: Number(capital),
        limit: Math.min(Number(limit), 500),
      });
      setCompareData(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setComparePending(false);
    }
  }

  const metricKeys = data?.metrics ? Object.entries(data.metrics) : [];

  return (
    <div>
      <section className="panel" style={{ padding: 16 }}>
        <div className="field-grid">
          <label className="field">
            <span className="field-label">Symbol</span>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Interval</span>
            <input value={interval} onChange={(e) => setInterval(e.target.value)} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Strategy</span>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="select">
              {strategyOptions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field-label">Capital</span>
            <input value={capital} onChange={(e) => setCapital(e.target.value)} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Candle limit</span>
            <input value={limit} onChange={(e) => setLimit(e.target.value)} className="input" />
          </label>
          <label className="field" style={{ gridColumn: "1 / -1" }}>
            <span className="field-label">Params (JSON)</span>
            <textarea
              value={paramsJson}
              onChange={(e) => setParamsJson(e.target.value)}
              rows={3}
              className="textarea"
              style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
            />
          </label>
        </div>

        <div className="button-row" style={{ marginTop: 14 }}>
          <button
            disabled={pending}
            onClick={() => { startTransition(() => { run().catch((e) => setError(String(e?.message ?? e))); }); }}
            className="button-primary"
          >
            {pending ? "Running..." : "Run backtest"}
          </button>
          <button
            disabled={comparePending}
            onClick={runCompare}
            className="button-secondary"
          >
            {comparePending ? "Comparing..." : "Compare all strategies"}
          </button>
          <button disabled={pending || comparePending} onClick={() => { setData(null); setCompareData(null); setError(null); }} className="button-secondary">
            Clear
          </button>
          {error ? <span style={{ color: "#fca5a5", fontWeight: 650 }}>{error}</span> : null}
        </div>
      </section>

      {compareData ? (
        <section style={{ marginTop: 14 }}>
          <SectionTitle>Strategy Comparison</SectionTitle>
          <div className="stats-grid">
            <Card label="Symbol" value={compareData.symbol} />
            <Card label="Interval" value={compareData.interval} />
            <Card label="Capital" value={fmtMoney(compareData.initial_capital)} />
            <Card label="Best" value={<Badge tone="success">{compareData.best_strategy ?? "None"}</Badge>} />
          </div>
          <Panel title="All strategies">
            <TableWrap>
              <table className="data-table" style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Strategy</th>
                    <th style={thStyle}>Trades</th>
                    <th style={thStyle}>Win Rate</th>
                    <th style={thStyle}>Profit Factor</th>
                    <th style={thStyle}>Sharpe</th>
                    <th style={thStyle}>Sortino</th>
                    <th style={thStyle}>Max DD</th>
                    <th style={thStyle}>ROI</th>
                    <th style={thStyle}>Final</th>
                    <th style={thStyle}>Valid</th>
                  </tr>
                </thead>
                <tbody>
                  {compareData.strategies.map((s) => {
                    const m = s.metrics;
                    const isBest = s.strategy_name === compareData.best_strategy;
                    return (
                      <tr key={s.strategy_name} style={isBest ? { background: "rgba(34, 197, 94, 0.06)" } : undefined}>
                        <td style={{ ...tdStyle, fontWeight: 800 }}>{s.strategy_name}{isBest ? " ★" : ""}</td>
                        <td style={tdStyle}>{String(m.total_trades ?? "-")}</td>
                        <td style={tdStyle}>{String(m.win_rate ?? "-")}%</td>
                        <td style={tdStyle}>{String(m.profit_factor ?? "-")}</td>
                        <td style={{ ...tdStyle, fontWeight: 700 }}>{String(m.sharpe_ratio ?? "-")}</td>
                        <td style={tdStyle}>{String(m.sortino_ratio ?? "-")}</td>
                        <td style={tdStyle}>{String(m.max_drawdown_pct ?? "-")}%</td>
                        <td style={tdStyle}>{String(m.roi_pct ?? "-")}%</td>
                        <td style={tdStyle}>{fmtMoney(Number(m.final_capital ?? 0))}</td>
                        <td style={tdStyle}><Badge tone={s.passed_validation ? "success" : "danger"}>{s.passed_validation ? "Yes" : "No"}</Badge></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
          </Panel>
        </section>
      ) : null}

      {data ? (
        <section style={{ marginTop: 14 }}>
          <SectionTitle>Single Strategy Result</SectionTitle>
          <div className="stats-grid">
            <Card label="Strategy" value={data.result.strategy_name} />
            <Card label="Final capital" value={fmtMoney(data.result.final_capital)} />
            <Card label="Fees" value={fmtMoney(data.result.total_fees)} />
            <Card label="Trades" value={String(Array.isArray(data.trades) ? data.trades.length : 0)} />
          </div>

          {metricKeys.length > 0 ? (
            <Panel title="Metrics">
              <div className="stats-grid">
                {metricKeys.map(([k, v]) => (
                  <Card key={k} label={k} value={typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(4)) : String(v ?? "-")} />
                ))}
              </div>
            </Panel>
          ) : null}

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontWeight: 800 }}>Trades (raw)</summary>
            <pre style={preStyle}>{JSON.stringify(data.trades, null, 2)}</pre>
          </details>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontWeight: 800 }}>Equity curve (raw)</summary>
            <pre style={preStyle}>{JSON.stringify(data.equity_curve.slice(0, 50), null, 2)}</pre>
            <p style={{ color: "#6b7280", marginTop: 6 }}>Mostrando solo los primeros 50 puntos.</p>
          </details>
        </section>
      ) : null}
    </div>
  );
}

function fmtMoney(v: number): string {
  if (!Number.isFinite(v)) return "-";
  return `$${v.toFixed(2)}`;
}
