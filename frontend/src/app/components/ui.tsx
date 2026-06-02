import React from "react";

export function Page({ title, subtitle, actions, children }: { title: string; subtitle?: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return (
    <main style={{ padding: 24, fontFamily: "system-ui" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>{title}</h1>
          {subtitle ? <p style={{ color: "#6b7280", marginTop: 6, marginBottom: 0 }}>{subtitle}</p> : null}
        </div>
        {actions ?? null}
      </div>
      <div style={{ marginTop: 12 }}>{children}</div>
    </main>
  );
}

export function Card({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12 }}>
      <div style={{ color: "#6b7280", fontSize: 12, fontWeight: 700 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 style={{ marginTop: 16, fontSize: 16, fontWeight: 900 }}>{children}</h2>;
}

export const thStyle: React.CSSProperties = { padding: 10, fontSize: 12, color: "#6b7280" };
export const preStyle: React.CSSProperties = {
  marginTop: 8,
  padding: 12,
  border: "1px solid #e5e7eb",
  borderRadius: 12,
  background: "#0b1020",
  color: "#e5e7eb",
  overflowX: "auto",
  fontSize: 12,
};
