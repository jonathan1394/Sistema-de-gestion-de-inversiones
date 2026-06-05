import Link from "next/link";

import { apiGet } from "@/lib/api";
import { Badge, Card, Page } from "@/app/components/ui";

type SystemHealth = { ok: boolean };

const quickLinks = [
  { href: "/overview", title: "Overview", text: "Resumen de modo, mercado y contexto operativo." },
  { href: "/market", title: "Market", text: "Consulta precio y velas con filtros rápidos." },
  { href: "/universe", title: "Universe", text: "Administra el universo oficial de simbolos evaluables." },
  { href: "/investment-review", title: "Review", text: "Vista unificada de datos, ranking, backtest y riesgo por activo." },
  { href: "/prospects", title: "Prospects", text: "Ranking y oportunidades para vigilar o activar." },
  { href: "/portfolio", title: "Portfolio", text: "Posiciones paper, snapshots y trazabilidad." },
  { href: "/risk", title: "Risk", text: "Evalúa operaciones antes de ejecutarlas." },
  { href: "/backtest", title: "Backtest", text: "Prueba estrategias y revisa métricas clave." },
];

export default async function Home() {
  const health = await apiGet<SystemHealth>("/system/health");

  return (
    <Page
      title="Centro de control"
      subtitle="Una entrada más clara para revisar estado del sistema, mercado, riesgo y portfolio sin perder tiempo entre pantallas."
      actions={<Badge tone={health.ok ? "success" : "danger"}>API {health.ok ? "Online" : "Offline"}</Badge>}
    >
      <section className="hero-grid">
        <Card label="Estado del sistema" value={health.ok ? "Conectado y listo" : "Revisar backend/API"} />
        <Card label="Flujo recomendado" value="Overview -> Market -> Prospects -> Risk" />
        <Card label="Uso ideal" value="Análisis diario, priorización y validación antes de operar" />
      </section>

      <div className="hero-links">
        {quickLinks.map((link) => (
          <Link key={link.href} href={link.href} className="hero-link">
            <div className="hero-link-title">{link.title}</div>
            <div className="hero-link-text">{link.text}</div>
          </Link>
        ))}
      </div>
    </Page>
  );
}
