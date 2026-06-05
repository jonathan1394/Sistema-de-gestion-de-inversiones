"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

type Props = {
  initialSymbol: string;
  initialInterval: string;
  initialAmount: string;
  symbolConfigured: boolean;
};

export function ReviewActions({ initialSymbol, initialInterval, initialAmount, symbolConfigured }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [interval, setInterval] = useState(initialInterval);
  const [amount, setAmount] = useState(initialAmount);
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function evaluateNewSymbol() {
    const cleanSymbol = symbol.trim().toUpperCase();
    if (!cleanSymbol) {
      setError("Enter a symbol first");
      return;
    }

    setError(null);
    setMessage(null);

    await apiPost("/prospecting/prospects/add", {
      symbol: cleanSymbol,
      interval,
      notes: notes.trim(),
    });
    await apiPost("/prospecting/scan", {
      symbol: cleanSymbol,
      interval,
    });

    setMessage(`Symbol ${cleanSymbol} added and scanned`);
    router.push(
      `/investment-review?symbol=${encodeURIComponent(cleanSymbol)}&interval=${encodeURIComponent(interval)}&amount=${encodeURIComponent(amount)}`,
    );
    router.refresh();
  }

  async function addToUniverse() {
    const cleanSymbol = symbol.trim().toUpperCase();
    if (!cleanSymbol) {
      setError("Enter a symbol first");
      return;
    }

    setError(null);
    setMessage(null);
    await apiPost("/config/universe-symbol", { symbol: cleanSymbol });
    setMessage(`Symbol ${cleanSymbol} added to the official universe`);
    router.refresh();
  }

  return (
    <section className="panel" style={{ padding: 16, marginTop: 14 }}>
      <div style={{ display: "grid", gap: 10 }}>
        <div>
          <div className="panel-title-inline">Evaluate a new symbol</div>
          <div style={{ color: "var(--muted)", marginTop: 4, lineHeight: 1.5 }}>
            Add the symbol as a prospect, run the scan and open the consolidated review in one step.
          </div>
        </div>

        <div className="field-grid">
          <label className="field">
            <span className="field-label">Symbol</span>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" placeholder="ADAUSDT" />
          </label>
          <label className="field">
            <span className="field-label">Interval</span>
            <select value={interval} onChange={(e) => setInterval(e.target.value)} className="select">
              <option value="1h">1h</option>
              <option value="4h">4h</option>
              <option value="1d">1d</option>
            </select>
          </label>
          <label className="field">
            <span className="field-label">Amount (USDT)</span>
            <input value={amount} onChange={(e) => setAmount(e.target.value)} className="input" />
          </label>
          <label className="field">
            <span className="field-label">Notes</span>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="input" placeholder="Optional context" />
          </label>
        </div>

        <div className="button-row">
          <button
            disabled={pending || !symbol.trim()}
            className="button-primary"
            onClick={() => {
              startTransition(() => {
                evaluateNewSymbol().catch((e) => setError(String(e?.message ?? e)));
              });
            }}
          >
            {pending ? "Adding and scanning..." : "Add, scan and review"}
          </button>
          {!symbolConfigured ? (
            <button
              disabled={pending || !symbol.trim()}
              className="button-secondary"
              onClick={() => {
                startTransition(() => {
                  addToUniverse().catch((e) => setError(String(e?.message ?? e)));
                });
              }}
            >
              {pending ? "Updating universe..." : "Add to official universe"}
            </button>
          ) : null}
        </div>

        {message ? <span style={{ color: "#a7f3d0", fontWeight: 700 }}>{message}</span> : null}
        {error ? <span style={{ color: "#fca5a5", fontWeight: 700 }}>{error}</span> : null}
      </div>
    </section>
  );
}
