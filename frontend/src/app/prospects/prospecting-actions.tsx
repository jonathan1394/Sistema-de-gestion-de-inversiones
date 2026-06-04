"use client";

import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

export function ProspectingActions() {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  async function runScanAll() {
    setError(null);
    setLastResult(null);
    const data = await apiPost<unknown[]>("/prospecting/scan", {});
    setLastResult(`Scan OK (count: ${data.length})`);
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
      <button
        disabled={pending}
        onClick={() => {
          startTransition(() => {
            runScanAll().catch((e) => setError(String(e?.message ?? e)));
          });
        }}
        style={{
          border: "1px solid #111827",
          borderRadius: 10,
          padding: "8px 10px",
          fontWeight: 700,
          background: pending ? "#f3f4f6" : "#111827",
          color: pending ? "#111827" : "white",
          cursor: pending ? "not-allowed" : "pointer",
        }}
      >
        {pending ? "Scanning..." : "Run Scan"}
      </button>
      <button
        disabled={pending}
        onClick={() => window.location.reload()}
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 10,
          padding: "8px 10px",
          fontWeight: 650,
          background: "white",
          cursor: pending ? "not-allowed" : "pointer",
        }}
      >
        Refresh
      </button>
      {lastResult ? <span style={{ color: "#065f46", fontWeight: 650 }}>{lastResult}</span> : null}
      {error ? <span style={{ color: "#b91c1c", fontWeight: 650 }}>{error}</span> : null}
    </div>
  );
}
