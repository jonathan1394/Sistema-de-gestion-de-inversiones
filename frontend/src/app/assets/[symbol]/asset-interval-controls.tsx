"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

export function AssetIntervalControls({ initialInterval }: { initialInterval: string }) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [interval, setInterval] = useState(initialInterval);
  const currentQuery = useMemo(() => new URLSearchParams(sp?.toString()), [sp]);

  return (
    <div className="button-row" style={{ marginTop: 12 }}>
      <label className="field" style={{ minWidth: 180 }}>
        <span className="field-label">Decision interval</span>
        <select value={interval} onChange={(e) => setInterval(e.target.value)} className="select">
          <option value="1h">1h</option>
          <option value="4h">4h</option>
          <option value="1d">1d</option>
        </select>
      </label>
      <button
        className="button-secondary"
        disabled={pending}
        onClick={() => {
          startTransition(() => {
            const q = new URLSearchParams(currentQuery.toString());
            q.set("interval", interval);
            router.push(`?${q.toString()}`);
          });
        }}
      >
        {pending ? "Updating..." : "Apply interval"}
      </button>
    </div>
  );
}
