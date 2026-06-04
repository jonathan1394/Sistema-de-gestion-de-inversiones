import { Badge, Card, Page, Panel, SectionTitle, preStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { CircuitBreakerStatus, RiskStatus } from "@/types";

import { RiskEvaluator } from "./risk-evaluator";

type Limits = Record<string, unknown>;

export default async function RiskPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const limits = await apiGet<Limits>("/risk/limits");
  const status = await apiGet<RiskStatus>("/risk/status");
  const circuitBreakers = await apiGet<CircuitBreakerStatus>("/risk/circuit-breakers");
  const params = (await searchParams) ?? {};
  const initialSymbol = typeof params.symbol === "string" ? params.symbol : "BTCUSDT";
  const risk = limits as {
    max_risk_per_trade_pct?: number;
    max_total_exposure_pct?: number;
    default_stop_loss_pct?: number;
    require_stop_loss?: boolean;
  };

  return (
    <Page
      title="Risk"
      subtitle="Límites (GET /risk/limits) + evaluación (POST /risk/evaluate)"
    >
      <section className="stats-grid">
        <Card label="Risk per trade" value={risk.max_risk_per_trade_pct != null ? `${(risk.max_risk_per_trade_pct * 100).toFixed(2)}%` : "-"} />
        <Card label="Total exposure" value={risk.max_total_exposure_pct != null ? `${(risk.max_total_exposure_pct * 100).toFixed(2)}%` : "-"} />
        <Card label="Default stop loss" value={risk.default_stop_loss_pct != null ? `${(risk.default_stop_loss_pct * 100).toFixed(2)}%` : "-"} />
        <Card label="Stop loss required" value={<Badge tone={risk.require_stop_loss ? "warning" : "info"}>{String(risk.require_stop_loss ?? false)}</Badge>} />
      </section>

      <SectionTitle>Status</SectionTitle>
      <section className="stats-grid">
        <Card label="App mode" value={status.mode} />
        <Card label="Kill switch" value={<Badge tone={status.kill_switch ? "danger" : "success"}>{String(status.kill_switch)}</Badge>} />
        <Card label="Circuit breakers" value={<Badge tone="info">{circuitBreakers.state}</Badge>} />
      </section>

      <SectionTitle>Limits</SectionTitle>
      <Panel title="Configuración activa de límites y protección">
        <pre style={preStyle}>{JSON.stringify(limits, null, 2)}</pre>
      </Panel>

      <SectionTitle>Evaluate</SectionTitle>
      <RiskEvaluator initialSymbol={initialSymbol} />
    </Page>
  );
}
