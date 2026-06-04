import React from "react";

export function Page({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="page">
      <div className="page-hero">
        <div>
          <div className="page-kicker">CriptoLab Web</div>
          <h1 className="page-title">{title}</h1>
          {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
        </div>
        {actions ? <div className="page-actions">{actions}</div> : null}
      </div>
      <div className="page-content">{children}</div>
    </main>
  );
}

export function Card({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className="card-value">{value}</div>
    </div>
  );
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="section-title">{children}</h2>;
}

export function Panel({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <section className="panel">
      {title ? <div className="panel-header">{title}</div> : null}
      {children}
    </section>
  );
}

export function TableWrap({ children }: { children: React.ReactNode }) {
  return <div className="table-wrap">{children}</div>;
}

export function Badge({
  children,
  tone = "info",
}: {
  children: React.ReactNode;
  tone?: "info" | "success" | "warning" | "danger";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export const thStyle: React.CSSProperties = {
  padding: "12px 14px",
  color: "var(--muted)",
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  fontWeight: 800,
};

export const tdStyle: React.CSSProperties = {
  padding: "13px 14px",
  verticalAlign: "top",
};

export const preStyle: React.CSSProperties = {
  marginTop: 8,
  padding: 14,
  border: "1px solid rgba(148, 163, 184, 0.14)",
  borderRadius: 16,
  background: "#08111f",
  color: "#dbeafe",
  overflowX: "auto",
  fontSize: 12,
};
