import { Page } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { Strategy } from "@/types";

import { BacktestRunner } from "./runner";

export default async function BacktestPage() {
  const strategies = await apiGet<Strategy[]>("/backtest/strategies");

  return (
    <Page title="Backtest" subtitle="Ejecución (POST /backtest/run)">
      <BacktestRunner strategies={strategies} />
    </Page>
  );
}
