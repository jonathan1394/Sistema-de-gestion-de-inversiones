"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

type Props = {
  initialSymbol: string;
  initialInterval: string;
  initialLimit: number;
};

const intervals = ["1h", "4h", "1d"];

export function MarketControls({ initialSymbol, initialInterval, initialLimit }: Props) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();

  const [symbol, setSymbol] = useState(initialSymbol);
  const [interval, setInterval] = useState(initialInterval);
  const [limit, setLimit] = useState(String(initialLimit));

  const currentQuery = useMemo(() => {
    const q = new URLSearchParams(sp?.toString());
    return q;
  }, [sp]);

  return (
    <section
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        padding: 12,
        display: "flex",
        gap: 12,
        alignItems: "end",
        flexWrap: "wrap",
      }}
    >
      <label style={{ display: "grid", gap: 6 }}>
        <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Symbol</span>
        <input value={symbol} onChange={(e) => setSymbol(e.target.value)} style={inputStyle} />
      </label>

      <label style={{ display: "grid", gap: 6 }}>
        <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Interval</span>
        <select value={interval} onChange={(e) => setInterval(e.target.value)} style={inputStyle}>
          {intervals.map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
          {intervals.includes(interval) ? null : <option value={interval}>{interval}</option>}
        </select>
      </label>

      <label style={{ display: "grid", gap: 6 }}>
        <span style={{ fontSize: 12, color: "#6b7280", fontWeight: 700 }}>Limit</span>
        <input value={limit} onChange={(e) => setLimit(e.target.value)} style={inputStyle} />
      </label>

      <button
        disabled={pending}
        onClick={() => {
          startTransition(() => {
            const q = new URLSearchParams(currentQuery.toString());
            q.set("symbol", symbol.trim().toUpperCase());
            q.set("interval", interval.trim());
            q.set("limit", String(Number(limit) || 200));
            router.push(`/market?${q.toString()}`);
          });
        }}
        style={primaryButtonStyle(pending)}
      >
        {pending ? "Loading..." : "Apply"}
      </button>
    </section>
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
