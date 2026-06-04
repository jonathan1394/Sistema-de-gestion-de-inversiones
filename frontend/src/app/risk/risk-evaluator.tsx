"use client";

import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

type RiskEvaluatePayload = {
  symbol: string;
  direction: string;
  entry_price: number;
  capital: number;
  confidence: number;
  reason: string;
  stop_loss_pct?: number;
};

export function RiskEvaluator({ initialSymbol = "BTCUSDT" }: { initialSymbol?: string }) {
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [direction, setDirection] = useState("BUY");
  const [entryPrice, setEntryPrice] = useState("0");
  const [capital, setCapital] = useState("1000");
  const [confidence, setConfidence] = useState("0.5");
  const [reason, setReason] = useState("UI evaluation");
  const [stopLossPct, setStopLossPct] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  async function evaluate() {
    setError(null);
    setResult(null);

    const payload: RiskEvaluatePayload = {
      symbol: symbol.trim().toUpperCase(),
      direction,
      entry_price: Number(entryPrice),
      capital: Number(capital),
      confidence: Number(confidence),
      reason,
    };
    if (stopLossPct.trim()) payload.stop_loss_pct = Number(stopLossPct);

    const data = await apiPost("/risk/evaluate", payload);
    setResult(data);
  }

  return (
    <div>
      <section className="panel" style={{ padding: 16 }}>
        <div className="field-grid">
        <Field label="Symbol">
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" />
        </Field>
        <Field label="Direction">
          <select value={direction} onChange={(e) => setDirection(e.target.value)} className="select">
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </Field>
        <Field label="Entry price">
          <input value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} className="input" />
        </Field>
        <Field label="Capital">
          <input value={capital} onChange={(e) => setCapital(e.target.value)} className="input" />
        </Field>
        <Field label="Confidence (0-1)">
          <input value={confidence} onChange={(e) => setConfidence(e.target.value)} className="input" />
        </Field>
        <Field label="Stop loss pct (optional)">
          <input
            value={stopLossPct}
            onChange={(e) => setStopLossPct(e.target.value)}
            placeholder="e.g. 0.02"
            className="input"
          />
        </Field>
        <Field label="Reason" full>
          <input value={reason} onChange={(e) => setReason(e.target.value)} className="input" />
        </Field>
        </div>

        <div className="button-row" style={{ marginTop: 14 }}>
          <button
            disabled={pending}
            onClick={() => {
              startTransition(() => {
                evaluate().catch((e) => setError(String(e?.message ?? e)));
              });
            }}
            className="button-primary"
          >
            {pending ? "Evaluating..." : "Evaluate"}
          </button>
          <button disabled={pending} onClick={() => setResult(null)} className="button-secondary">
            Clear
          </button>
          {error ? <span style={{ color: "#fca5a5", fontWeight: 650 }}>{error}</span> : null}
        </div>
      </section>

      {result ? (
        <details style={{ marginTop: 12 }} open>
          <summary style={{ cursor: "pointer", fontWeight: 800 }}>Result</summary>
          <pre style={preStyle}>{JSON.stringify(result, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

function Field({ label, full, children }: { label: string; full?: boolean; children: React.ReactNode }) {
  return (
    <label className="field" style={{ gridColumn: full ? "1 / -1" : undefined }}>
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
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
