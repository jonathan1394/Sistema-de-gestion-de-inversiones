import { Page } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { BacktestRunner } from "./runner";

type Strategy = { id: string; label: string };

export default async function BacktestPage() {
  const strategies = await apiGet<Strategy[]>("/backtest/strategies");

  return (
    <Page title="Backtest" subtitle="Ejecución (POST /backtest/run)">
      <BacktestRunner strategies={strategies} />
    </Page>
  );
}
