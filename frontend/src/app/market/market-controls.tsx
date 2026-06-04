"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

type Props = {
  initialSymbol: string;
  initialInterval: string;
  initialLimit: number;
  initialStartMs: string;
  initialEndMs: string;
  initialDesc: boolean;
};

const intervals = ["1h", "4h", "1d"];

export function MarketControls({ initialSymbol, initialInterval, initialLimit, initialStartMs, initialEndMs, initialDesc }: Props) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();

  const [symbol, setSymbol] = useState(initialSymbol);
  const [interval, setInterval] = useState(initialInterval);
  const [limit, setLimit] = useState(String(initialLimit));
  const [startMs, setStartMs] = useState(initialStartMs);
  const [endMs, setEndMs] = useState(initialEndMs);
  const [desc, setDesc] = useState(initialDesc);

  const currentQuery = useMemo(() => {
    const q = new URLSearchParams(sp?.toString());
    return q;
  }, [sp]);

  return (
    <section className="panel" style={{ padding: 16 }}>
      <div className="field-grid">
      <label className="field">
        <span className="field-label">Symbol</span>
        <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" />
      </label>

      <label className="field">
        <span className="field-label">Interval</span>
        <select value={interval} onChange={(e) => setInterval(e.target.value)} className="select">
          {intervals.map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
          {intervals.includes(interval) ? null : <option value={interval}>{interval}</option>}
        </select>
      </label>

      <label className="field">
        <span className="field-label">Limit</span>
        <input value={limit} onChange={(e) => setLimit(e.target.value)} className="input" />
      </label>

      <label className="field">
        <span className="field-label">Start ms</span>
        <input value={startMs} onChange={(e) => setStartMs(e.target.value)} className="input" placeholder="1704067200000" />
      </label>

      <label className="field">
        <span className="field-label">End ms</span>
        <input value={endMs} onChange={(e) => setEndMs(e.target.value)} className="input" placeholder="1711929600000" />
      </label>
      </div>

      <div className="button-row" style={{ marginTop: 14 }}>
        <label className="button-secondary" style={{ gap: 8 }}>
          <input type="checkbox" checked={desc} onChange={(e) => setDesc(e.target.checked)} />
          Descending order
        </label>

      <button
        className="button-primary"
        disabled={pending}
        onClick={() => {
          startTransition(() => {
            const q = new URLSearchParams(currentQuery.toString());
            q.set("symbol", symbol.trim().toUpperCase());
            q.set("interval", interval.trim());
            q.set("limit", String(Number(limit) || 200));
            if (startMs.trim()) q.set("start_ms", startMs.trim());
            else q.delete("start_ms");
            if (endMs.trim()) q.set("end_ms", endMs.trim());
            else q.delete("end_ms");
            if (desc) q.set("desc", "true");
            else q.delete("desc");
            router.push(`/market?${q.toString()}`);
          });
        }}
      >
        {pending ? "Loading..." : "Apply"}
      </button>
      </div>
    </section>
  );
}
