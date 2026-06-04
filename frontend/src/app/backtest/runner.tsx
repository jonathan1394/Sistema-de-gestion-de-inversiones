"use client";

import { useMemo, useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

type Strategy = { id: string; label: string };

type Props = {
  strategies: Strategy[];
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

export function BacktestRunner({ strategies }: Props) {
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState("BTCUSDT");
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
      <section
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          padding: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Symbol</span>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} style={inputStyle} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Interval</span>
          <input value={interval} onChange={(e) => setInterval(e.target.value)} style={inputStyle} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Strategy</span>
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)} style={inputStyle}>
            {strategyOptions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Capital</span>
          <input value={capital} onChange={(e) => setCapital(e.target.value)} style={inputStyle} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Candle limit</span>
          <input value={limit} onChange={(e) => setLimit(e.target.value)} style={inputStyle} />
        </label>
        <label style={{ display: "grid", gap: 6, gridColumn: "1 / -1" }}>
          <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Params (JSON)</span>
          <textarea
            value={paramsJson}
            onChange={(e) => setParamsJson(e.target.value)}
            rows={4}
            style={{ ...inputStyle, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
          />
        </label>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button
            disabled={pending}
            onClick={() => {
              startTransition(() => {
                run().catch((e) => setError(String(e?.message ?? e)));
              });
            }}
            style={primaryButtonStyle(pending)}
          >
            {pending ? "Running..." : "Run backtest"}
          </button>
          <button disabled={pending} onClick={() => setData(null)} style={secondaryButtonStyle(pending)}>
            Clear result
          </button>
          {error ? <span style={{ color: "#b91c1c", fontWeight: 650 }}>{error}</span> : null}
        </div>
      </section>

      {data ? (
        <section style={{ marginTop: 14 }}>
          <h2 style={{ fontSize: 16, fontWeight: 800 }}>Result</h2>
          <div
            style={{
              marginTop: 8,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
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

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12 }}>
      <div style={{ color: "#6b7280", fontSize: 12, fontWeight: 700 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}

function fmtMoney(v: number): string {
  if (!Number.isFinite(v)) return "-";
  return `$${v.toFixed(2)}`;
}

const inputStyle: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: 10,
  padding: "8px 10px",
  fontWeight: 650,
};

function primaryButtonStyle(pending: boolean): React.CSSProperties {
  return {
    border: "1px solid #111827",
    borderRadius: 10,
    padding: "8px 10px",
    fontWeight: 800,
    background: pending ? "#f3f4f6" : "#111827",
    color: pending ? "#111827" : "white",
    cursor: pending ? "not-allowed" : "pointer",
  };
}

function secondaryButtonStyle(pending: boolean): React.CSSProperties {
  return {
    border: "1px solid #e5e7eb",
    borderRadius: 10,
    padding: "8px 10px",
    fontWeight: 650,
    background: "white",
    cursor: pending ? "not-allowed" : "pointer",
  };
}

const preStyle: React.CSSProperties = {
  marginTop: 8,
  padding: 12,
  border: "1px solid #e5e7eb",
  borderRadius: 12,
  background: "#0b1020",
  color: "#e5e7eb",
  overflowX: "auto",
  fontSize: 12,
};
