"use client";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ fontSize: 20, fontWeight: 800, color: "#b91c1c" }}>Something went wrong</h1>
      <p style={{ color: "#6b7280", marginTop: 8 }}>{error.message}</p>
      <button
        onClick={() => reset()}
        style={{
          marginTop: 12,
          border: "1px solid #111827",
          borderRadius: 10,
          padding: "8px 16px",
          fontWeight: 700,
          background: "#111827",
          color: "white",
          cursor: "pointer",
        }}
      >
        Try again
      </button>
    </main>
  );
}
