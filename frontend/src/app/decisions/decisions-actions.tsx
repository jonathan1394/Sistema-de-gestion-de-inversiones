"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

export function DecisionsActions({
  initialSymbol,
  initialApprovedOnly,
  initialRejectedOnly,
  initialPage,
}: {
  initialSymbol: string;
  initialApprovedOnly: boolean;
  initialRejectedOnly: boolean;
  initialPage: number;
}) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [approvedOnly, setApprovedOnly] = useState(initialApprovedOnly);
  const [rejectedOnly, setRejectedOnly] = useState(initialRejectedOnly);

  const currentQuery = useMemo(() => new URLSearchParams(sp?.toString()), [sp]);

  function push(page: number) {
    const q = new URLSearchParams(currentQuery.toString());
    if (symbol.trim()) q.set("symbol", symbol.trim().toUpperCase());
    else q.delete("symbol");
    if (approvedOnly) q.set("approved_only", "true");
    else q.delete("approved_only");
    if (rejectedOnly) q.set("rejected_only", "true");
    else q.delete("rejected_only");
    q.set("page", String(page));
    q.set("limit", "50");
    router.push(`/decisions?${q.toString()}`);
  }

  return (
    <div style={{ display: "grid", gap: 12, minWidth: 420 }}>
      <div className="field-grid">
        <label className="field">
          <span className="field-label">Symbol</span>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" placeholder="BTCUSDT" />
        </label>
      </div>

      <div className="button-row">
        <label className="button-secondary" style={{ gap: 8 }}>
          <input type="checkbox" checked={approvedOnly} onChange={(e) => setApprovedOnly(e.target.checked)} />
          Approved only
        </label>
        <label className="button-secondary" style={{ gap: 8 }}>
          <input type="checkbox" checked={rejectedOnly} onChange={(e) => setRejectedOnly(e.target.checked)} />
          Rejected only
        </label>
      </div>

      <div className="button-row">
        <button
          className="button-primary"
          disabled={pending}
          onClick={() => {
            startTransition(() => push(1));
          }}
        >
          {pending ? "Applying..." : "Apply filters"}
        </button>
        <button className="button-secondary" disabled={pending || initialPage <= 1} onClick={() => push(Math.max(1, initialPage - 1))}>
          Previous
        </button>
        <button className="button-secondary" disabled={pending} onClick={() => push(initialPage + 1)}>
          Next
        </button>
        <button className="button-secondary" disabled={pending} onClick={() => router.push("/decisions")}>Reset</button>
      </div>
    </div>
  );
}
