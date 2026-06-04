"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

export function PortfolioActions({ initialSymbol, initialPage }: { initialSymbol: string; initialPage: number }) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState(initialSymbol);
  const currentQuery = useMemo(() => new URLSearchParams(sp?.toString()), [sp]);

  function push(page: number) {
    const q = new URLSearchParams(currentQuery.toString());
    if (symbol.trim()) q.set("symbol", symbol.trim().toUpperCase());
    else q.delete("symbol");
    q.set("page", String(page));
    q.set("limit", "100");
    router.push(`/portfolio?${q.toString()}`);
  }

  return (
    <div className="button-row">
      <label className="field" style={{ minWidth: 180 }}>
        <span className="field-label">Trade symbol filter</span>
        <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" placeholder="BTCUSDT" />
      </label>
      <button className="button-primary" disabled={pending} onClick={() => startTransition(() => push(1))}>{pending ? "Applying..." : "Apply"}</button>
      <button className="button-secondary" disabled={pending || initialPage <= 1} onClick={() => push(Math.max(1, initialPage - 1))}>Previous</button>
      <button className="button-secondary" disabled={pending} onClick={() => push(initialPage + 1)}>Next</button>
      <button className="button-secondary" disabled={pending} onClick={() => router.push("/portfolio")}>Reset</button>
    </div>
  );
}
