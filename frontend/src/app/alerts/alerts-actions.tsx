"use client";

import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

export function AlertsActions() {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function clearHistory() {
    setError(null);
    setInfo(null);
    await apiPost("/alerts/history/clear");
    setInfo("Historial limpiado");
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
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
      <button
        disabled={pending}
        onClick={() => {
          startTransition(() => {
            clearHistory()
              .then(() => window.location.reload())
              .catch((e) => setError(String(e?.message ?? e)));
          });
        }}
        style={{
          border: "1px solid #b91c1c",
          borderRadius: 10,
          padding: "8px 10px",
          fontWeight: 800,
          background: pending ? "#f3f4f6" : "#fff",
          color: "#b91c1c",
          cursor: pending ? "not-allowed" : "pointer",
        }}
      >
        Clear history
      </button>
      {info ? <span style={{ color: "#065f46", fontWeight: 650 }}>{info}</span> : null}
      {error ? <span style={{ color: "#b91c1c", fontWeight: 650 }}>{error}</span> : null}
    </div>
  );
}
