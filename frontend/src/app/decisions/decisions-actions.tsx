"use client";

export function DecisionsActions() {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      <button
        onClick={() => window.location.reload()}
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 10,
          padding: "8px 10px",
          fontWeight: 650,
          background: "white",
          cursor: "pointer",
        }}
      >
        Refresh
      </button>
    </div>
  );
}
