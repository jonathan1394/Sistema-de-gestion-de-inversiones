import Link from "next/link";

import { apiGet } from "@/lib/api";

type SystemHealth = { ok: boolean };

export default async function Home() {
  const health = await apiGet<SystemHealth>("/system/health");

  return (
    <main style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>CriptoLab (Web)</h1>
      <p style={{ marginBottom: 16, color: "#555" }}>
        Estado API: <b>{health.ok ? "OK" : "ERROR"}</b>
      </p>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link href="/overview">Overview</Link>
        <Link href="/market">Market</Link>
        <Link href="/prospects">Prospects</Link>
        <Link href="/backtest">Backtest</Link>
        <Link href="/portfolio">Portfolio</Link>
        <Link href="/risk">Risk</Link>
        <Link href="/alerts">Alerts</Link>
        <Link href="/decisions">Decisions</Link>
      </div>
    </main>
  );
}
