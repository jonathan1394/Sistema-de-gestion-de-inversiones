import { Badge, Card, Page } from "@/app/components/ui";
import { apiGet } from "@/lib/api";
import type { Config } from "@/types";

import { UniverseManager } from "./universe-manager";

export default async function UniversePage() {
  const config = await apiGet<Config>("/config");
  const symbols = config.symbols ?? [];

  return (
    <Page
      title="Universe"
      subtitle="Gestion del universo oficial de simbolos evaluables"
      actions={<Badge tone="info">{symbols.length} symbols</Badge>}
    >
      <section className="stats-grid">
        <Card label="Configured symbols" value={String(symbols.length)} />
        <Card label="Timeframes" value={config.timeframes?.join(", ") ?? "-"} />
        <Card label="App mode" value={config.mode} />
        <Card label="Kill switch" value={String(config.kill_switch)} />
      </section>

      <UniverseManager initialSymbols={symbols} />
    </Page>
  );
}
