import { Page } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { Strategy } from "@/types";

import { BacktestRunner } from "./runner";

export default async function BacktestPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const strategies = await apiGet<Strategy[]>("/backtest/strategies");
  const params = (await searchParams) ?? {};
  const initialSymbol = typeof params.symbol === "string" ? params.symbol : "BTCUSDT";

  return (
    <Page title="Backtest" subtitle="Ejecución (POST /backtest/run)">
      <BacktestRunner strategies={strategies} initialSymbol={initialSymbol} />
    </Page>
  );
}
