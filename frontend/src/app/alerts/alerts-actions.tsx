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
    <div className="button-row">
      <button disabled={pending} onClick={() => window.location.reload()} className="button-secondary">
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
        className="button-danger"
      >
        Clear history
      </button>
      {info ? <span style={{ color: "#a7f3d0", fontWeight: 650 }}>{info}</span> : null}
      {error ? <span style={{ color: "#fca5a5", fontWeight: 650 }}>{error}</span> : null}
    </div>
  );
}
