"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

export function PortfolioActions({ initialSymbol, initialPage }: { initialSymbol: string; initialPage: number }) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [tradeSymbol, setTradeSymbol] = useState("");
  const [tradeAmount, setTradeAmount] = useState("50");
  const [tradeReason, setTradeReason] = useState("");
  const [tradeResult, setTradeResult] = useState<string | null>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const currentQuery = useMemo(() => new URLSearchParams(sp?.toString()), [sp]);

  function push(page: number) {
    const q = new URLSearchParams(currentQuery.toString());
    if (symbol.trim()) q.set("symbol", symbol.trim().toUpperCase());
    else q.delete("symbol");
    q.set("page", String(page));
    q.set("limit", "100");
    router.push(`/portfolio?${q.toString()}`);
  }

  async function executeTrade(action: "buy" | "sell") {
    setTradeResult(null);
    setTradeError(null);
    if (!tradeSymbol.trim()) { setTradeError("Symbol required"); return; }
    try {
      const res = await apiPost<Record<string, unknown>>("/portfolio/trade", {
        symbol: tradeSymbol.trim().toUpperCase(),
        action,
        amount_usdt: Number(tradeAmount) || 50,
        reason: tradeReason || `Manual paper ${action}`,
      });
      setTradeResult(`${action.toUpperCase()} ${res.quantity} ${tradeSymbol.toUpperCase()} @ $${Number(res.price).toFixed(2)}`);
      router.refresh();
    } catch (e) {
      setTradeError(String(e));
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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

      <div className="panel" style={{ padding: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 10, fontSize: 13 }}>Paper trade execution</div>
        <div className="field-grid">
          <label className="field">
            <span className="field-label">Symbol</span>
            <input value={tradeSymbol} onChange={(e) => setTradeSymbol(e.target.value)} className="input" placeholder="BTCUSDT" />
          </label>
          <label className="field">
            <span className="field-label">Amount (USDT)</span>
            <input value={tradeAmount} onChange={(e) => setTradeAmount(e.target.value)} className="input" type="number" />
          </label>
          <label className="field" style={{ gridColumn: "1 / -1" }}>
            <span className="field-label">Reason</span>
            <input value={tradeReason} onChange={(e) => setTradeReason(e.target.value)} className="input" placeholder="Optional reason" />
          </label>
        </div>
        <div className="button-row" style={{ marginTop: 10 }}>
          <button className="button-primary" onClick={() => executeTrade("buy")}>Buy</button>
          <button className="button-secondary" onClick={() => executeTrade("sell")}>Sell</button>
          {tradeResult ? <span style={{ color: "#86efac", fontWeight: 700 }}>{tradeResult}</span> : null}
          {tradeError ? <span style={{ color: "#fca5a5", fontWeight: 700 }}>{tradeError}</span> : null}
        </div>
      </div>
    </div>
  );
}
