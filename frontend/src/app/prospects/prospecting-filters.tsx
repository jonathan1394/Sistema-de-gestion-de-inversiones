"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

export function ProspectingFilters({
  initialStatus,
  initialMinScore,
}: {
  initialStatus: string;
  initialMinScore: string;
}) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [status, setStatus] = useState(initialStatus);
  const [minScore, setMinScore] = useState(initialMinScore);

  const currentQuery = useMemo(() => new URLSearchParams(sp?.toString()), [sp]);

  return (
    <section className="panel" style={{ padding: 16 }}>
      <div className="field-grid">
        <label className="field">
          <span className="field-label">Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="select">
            <option value="">All</option>
            <option value="watching">watching</option>
            <option value="active">active</option>
            <option value="archived">archived</option>
          </select>
        </label>

        <label className="field">
          <span className="field-label">Min score</span>
          <input value={minScore} onChange={(e) => setMinScore(e.target.value)} className="input" placeholder="e.g. 0.50" />
        </label>
      </div>

      <div className="button-row" style={{ marginTop: 14 }}>
        <button
          className="button-primary"
          disabled={pending}
          onClick={() => {
            startTransition(() => {
              const q = new URLSearchParams(currentQuery.toString());
              if (status) q.set("status", status);
              else q.delete("status");
              if (minScore.trim()) q.set("min_score", minScore.trim());
              else q.delete("min_score");
              router.push(`/prospects?${q.toString()}`);
            });
          }}
        >
          {pending ? "Applying..." : "Apply filters"}
        </button>
        <button
          className="button-secondary"
          disabled={pending}
          onClick={() => {
            setStatus("");
            setMinScore("");
            router.push("/prospects");
          }}
        >
          Reset
        </button>
      </div>
    </section>
  );
}
