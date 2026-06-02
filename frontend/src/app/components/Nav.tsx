"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links: Array<{ href: string; label: string }> = [
  { href: "/", label: "Home" },
  { href: "/overview", label: "Overview" },
  { href: "/market", label: "Market" },
  { href: "/prospects", label: "Prospects" },
  { href: "/ranking", label: "Ranking" },
  { href: "/backtest", label: "Backtest" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/risk", label: "Risk" },
  { href: "/alerts", label: "Alerts" },
  { href: "/decisions", label: "Decisions" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        display: "flex",
        gap: 12,
        flexWrap: "wrap",
        padding: "12px 16px",
        borderBottom: "1px solid #e5e7eb",
        position: "sticky",
        top: 0,
        background: "white",
        zIndex: 10,
      }}
    >
      {links.map((l) => {
        const active = pathname === l.href;
        return (
          <Link
            key={l.href}
            href={l.href}
            style={{
              textDecoration: "none",
              color: active ? "#111827" : "#374151",
              fontWeight: active ? 700 : 600,
            }}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
