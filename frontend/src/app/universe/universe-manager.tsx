"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

export function UniverseManager({ initialSymbols }: { initialSymbols: string[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function addSymbol() {
    const cleanSymbol = symbol.trim().toUpperCase();
    if (!cleanSymbol) {
      setError("Enter a symbol first");
      return;
    }
    setError(null);
    setMessage(null);
    await apiPost("/config/universe-symbol", { symbol: cleanSymbol });
    setMessage(`${cleanSymbol} added to the official universe`);
    setSymbol("");
    router.refresh();
  }

  async function removeSymbol(target: string) {
    setError(null);
    setMessage(null);
    await apiPost("/config/universe-symbol/remove", { symbol: target });
    setMessage(`${target} removed from the official universe`);
    router.refresh();
  }

  return (
    <>
      <section className="panel" style={{ padding: 16 }}>
        <div className="field-grid">
          <label className="field">
            <span className="field-label">Add symbol</span>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" placeholder="ADAUSDT" />
          </label>
        </div>
        <div className="button-row" style={{ marginTop: 14 }}>
          <button
            disabled={pending || !symbol.trim()}
            className="button-primary"
            onClick={() => {
              startTransition(() => {
                addSymbol().catch((e) => setError(String(e?.message ?? e)));
              });
            }}
          >
            {pending ? "Updating..." : "Add symbol"}
          </button>
        </div>
        {message ? <span style={{ color: "#a7f3d0", fontWeight: 700 }}>{message}</span> : null}
        {error ? <span style={{ color: "#fca5a5", fontWeight: 700 }}>{error}</span> : null}
      </section>

      <section className="panel" style={{ marginTop: 14 }}>
        <div className="panel-header">Official universe</div>
        <div className="universe-grid">
          {initialSymbols.map((item) => (
            <div key={item} className="universe-chip">
              <span style={{ fontWeight: 800 }}>{item}</span>
              <button
                disabled={pending}
                className="button-danger"
                style={{ minHeight: 32, padding: "0.45rem 0.75rem" }}
                onClick={() => {
                  startTransition(() => {
                    removeSymbol(item).catch((e) => setError(String(e?.message ?? e)));
                  });
                }}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
