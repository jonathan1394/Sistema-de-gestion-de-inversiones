import { Page, SectionTitle, preStyle } from "@/app/components/ui";
import { apiGet } from "@/lib/api";

import { RiskEvaluator } from "./risk-evaluator";

type Limits = Record<string, unknown>;

export default async function RiskPage() {
  const limits = await apiGet<Limits>("/risk/limits");

  return (
    <Page
      title="Risk"
      subtitle="Límites (GET /risk/limits) + evaluación (POST /risk/evaluate)"
    >
      <SectionTitle>Limits</SectionTitle>
      <pre style={preStyle}>{JSON.stringify(limits, null, 2)}</pre>

      <SectionTitle>Evaluate</SectionTitle>
      <RiskEvaluator />
    </Page>
  );
}
