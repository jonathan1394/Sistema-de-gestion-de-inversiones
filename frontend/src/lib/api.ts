export type ApiEnvelope<T> = {
  status: "ok" | "error";
  data: T;
  error: null | { message: string; type?: string; details?: Record<string, unknown> };
  meta: Record<string, unknown>;
};

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function apiBase(): string {
  // In dev, we call the Python API directly.
  // In prod, you can set NEXT_PUBLIC_API_BASE or use Next rewrites.
  return process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  const text = await res.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }

  if (!res.ok) {
    throw new ApiError(`HTTP ${res.status}`, res.status, payload);
  }

  const env = payload as ApiEnvelope<T>;
  if (!env || typeof env !== "object" || (env as any).status !== "ok") {
    throw new ApiError("Unexpected API response", res.status, payload);
  }
  return env.data;
}
