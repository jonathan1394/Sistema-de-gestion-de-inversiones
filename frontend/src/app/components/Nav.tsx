"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links: Array<{ href: string; label: string }> = [
  { href: "/", label: "Home" },
  { href: "/overview", label: "Overview" },
  { href: "/market", label: "Market" },
  { href: "/market-analysis", label: "Analysis" },
  { href: "/prospects", label: "Prospects" },
  { href: "/ranking", label: "Ranking" },
  { href: "/backtest", label: "Backtest" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/risk", label: "Risk" },
  { href: "/journal", label: "Journal" },
  { href: "/alerts", label: "Alerts" },
  { href: "/decisions", label: "Decisions" },
  { href: "/logs", label: "Logs" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <span className="brand-title">CriptoLab</span>
          <span className="brand-subtitle">Panel operativo, señales y control de riesgo</span>
        </div>

        <nav className="nav-links" aria-label="Main navigation">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link key={l.href} href={l.href} className={`nav-link${active ? " active" : ""}`}>
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
