"use client";

import { useMemo, useState, useTransition } from "react";

import { Card, preStyle } from "@/app/components/ui";
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

  const strategyOptions = useMemo(() => strategies, [strategies]);

  async function run() {
    setError(null);
    setData(null);

    let params: Record<string, unknown> = {};
    try {
      params = paramsJson.trim() ? JSON.parse(paramsJson) : {};
    } catch {
      throw new Error("params JSON inválido");
    }

    const payload = {
      symbol: symbol.trim().toUpperCase(),
      interval: interval.trim(),
      strategy,
      capital: Number(capital),
      limit: Number(limit),
      params,
    };

    const data = await apiPost<BacktestResponse>("/backtest/run", payload);
    setData(data);
  }

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
              rows={4}
              className="textarea"
              style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
            />
          </label>
        </div>

        <div className="button-row" style={{ marginTop: 14 }}>
          <button
            disabled={pending}
            onClick={() => {
              startTransition(() => {
                run().catch((e) => setError(String(e?.message ?? e)));
              });
            }}
            className="button-primary"
          >
            {pending ? "Running..." : "Run backtest"}
          </button>
          <button disabled={pending} onClick={() => setData(null)} className="button-secondary">
            Clear result
          </button>
          {error ? <span style={{ color: "#fca5a5", fontWeight: 650 }}>{error}</span> : null}
        </div>
      </section>

      {data ? (
        <section style={{ marginTop: 14 }}>
          <h2 className="section-title">Result</h2>
          <div className="stats-grid">
            <Card label="Strategy" value={data.result.strategy_name} />
            <Card label="Final capital" value={fmtMoney(data.result.final_capital)} />
            <Card label="Fees" value={fmtMoney(data.result.total_fees)} />
            <Card label="Trades" value={String(Array.isArray(data.trades) ? data.trades.length : 0)} />
          </div>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontWeight: 800 }}>Metrics (raw)</summary>
            <pre style={preStyle}>{JSON.stringify(data.metrics, null, 2)}</pre>
          </details>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontWeight: 800 }}>Trades (raw)</summary>
            <pre style={preStyle}>{JSON.stringify(data.trades, null, 2)}</pre>
          </details>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontWeight: 800 }}>Equity curve (raw)</summary>
            <pre style={preStyle}>{JSON.stringify(data.equity_curve.slice(0, 50), null, 2)}</pre>
            <p style={{ color: "#6b7280", marginTop: 6 }}>
              Mostrando solo los primeros 50 puntos.
            </p>
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
