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

export function RiskEvaluator() {
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState("BTCUSDT");
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
        <Field label="Symbol">
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Direction">
          <select value={direction} onChange={(e) => setDirection(e.target.value)} style={inputStyle}>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </Field>
        <Field label="Entry price">
          <input value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Capital">
          <input value={capital} onChange={(e) => setCapital(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Confidence (0-1)">
          <input value={confidence} onChange={(e) => setConfidence(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Stop loss pct (optional)">
          <input
            value={stopLossPct}
            onChange={(e) => setStopLossPct(e.target.value)}
            placeholder="e.g. 0.02"
            style={inputStyle}
          />
        </Field>
        <Field label="Reason" full>
          <input value={reason} onChange={(e) => setReason(e.target.value)} style={inputStyle} />
        </Field>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button
            disabled={pending}
            onClick={() => {
              startTransition(() => {
                evaluate().catch((e) => setError(String(e?.message ?? e)));
              });
            }}
            style={primaryButtonStyle(pending)}
          >
            {pending ? "Evaluating..." : "Evaluate"}
          </button>
          <button disabled={pending} onClick={() => setResult(null)} style={secondaryButtonStyle(pending)}>
            Clear
          </button>
          {error ? <span style={{ color: "#b91c1c", fontWeight: 650 }}>{error}</span> : null}
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
    <label style={{ display: "grid", gap: 6, gridColumn: full ? "1 / -1" : undefined }}>
      <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>{label}</span>
      {children}
    </label>
  );
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
