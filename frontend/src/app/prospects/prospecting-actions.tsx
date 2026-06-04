"use client";

import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

export function ProspectingActions() {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("");
  const [interval, setInterval] = useState("1d");
  const [newProspectSymbol, setNewProspectSymbol] = useState("");
  const [newProspectNotes, setNewProspectNotes] = useState("");

  async function runScanAll() {
    setError(null);
    setLastResult(null);
    const payload = symbol.trim() ? { symbol: symbol.trim().toUpperCase(), interval } : {};
    const data = await apiPost<unknown[] | Record<string, unknown> | null>("/prospecting/scan", payload);
    if (Array.isArray(data)) {
      setLastResult(`Scan OK (count: ${data.length})`);
      return;
    }
    setLastResult(data ? `Scan OK for ${symbol.trim().toUpperCase()}` : "No data returned");
  }

  async function addProspect() {
    setError(null);
    setLastResult(null);
    await apiPost("/prospecting/prospects/add", {
      symbol: newProspectSymbol.trim().toUpperCase(),
      interval,
      notes: newProspectNotes.trim(),
    });
    setLastResult(`Prospect ${newProspectSymbol.trim().toUpperCase()} added`);
    window.location.reload();
  }

  return (
    <div style={{ display: "grid", gap: 12, minWidth: 320 }}>
      <div className="field-grid">
        <label className="field">
          <span className="field-label">Scan symbol</span>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" placeholder="Empty = scan all" />
        </label>
        <label className="field">
          <span className="field-label">Interval</span>
          <select value={interval} onChange={(e) => setInterval(e.target.value)} className="select">
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1d">1d</option>
          </select>
        </label>
      </div>

      <div className="button-row">
      <button
        disabled={pending}
        onClick={() => {
          startTransition(() => {
            runScanAll().catch((e) => setError(String(e?.message ?? e)));
          });
        }}
        className="button-primary"
      >
        {pending ? "Scanning..." : "Run Scan"}
      </button>
      <button disabled={pending} onClick={() => window.location.reload()} className="button-secondary">
        Refresh
      </button>
      </div>

      <div className="field-grid">
        <label className="field">
          <span className="field-label">Add prospect</span>
          <input value={newProspectSymbol} onChange={(e) => setNewProspectSymbol(e.target.value)} className="input" placeholder="BTCUSDT" />
        </label>
        <label className="field">
          <span className="field-label">Notes</span>
          <input value={newProspectNotes} onChange={(e) => setNewProspectNotes(e.target.value)} className="input" placeholder="Optional context" />
        </label>
      </div>

      <div className="button-row">
        <button
          disabled={pending || !newProspectSymbol.trim()}
          className="button-secondary"
          onClick={() => {
            startTransition(() => {
              addProspect().catch((e) => setError(String(e?.message ?? e)));
            });
          }}
        >
          Add prospect
        </button>
      </div>

      {lastResult ? <span style={{ color: "#a7f3d0", fontWeight: 650 }}>{lastResult}</span> : null}
      {error ? <span style={{ color: "#fca5a5", fontWeight: 650 }}>{error}</span> : null}
    </div>
  );
}
