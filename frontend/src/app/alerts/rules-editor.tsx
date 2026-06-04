"use client";

import { useState, useTransition } from "react";

import { apiPost } from "@/lib/api";

export function RulesEditor({ initialRules }: { initialRules: Record<string, unknown> }) {
  const [pending, startTransition] = useTransition();
  const [jsonValue, setJsonValue] = useState(JSON.stringify(initialRules, null, 2));
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function saveRules() {
    setInfo(null);
    setError(null);
    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(jsonValue);
    } catch {
      throw new Error("Invalid JSON rules payload");
    }
    await apiPost("/alerts/rules", payload);
    setInfo("Rules saved successfully");
    window.location.reload();
  }

  return (
    <div>
      <label className="field">
        <span className="field-label">Rules JSON</span>
        <textarea
          value={jsonValue}
          onChange={(e) => setJsonValue(e.target.value)}
          rows={14}
          className="textarea"
          style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
        />
      </label>

      <div className="button-row" style={{ marginTop: 14 }}>
        <button
          className="button-primary"
          disabled={pending}
          onClick={() => {
            startTransition(() => {
              saveRules().catch((e) => setError(String(e?.message ?? e)));
            });
          }}
        >
          {pending ? "Saving..." : "Save rules"}
        </button>
      </div>

      {info ? <p style={{ marginTop: 10, color: "#a7f3d0" }}>{info}</p> : null}
      {error ? <p style={{ marginTop: 10, color: "#fca5a5" }}>{error}</p> : null}
    </div>
  );
}
