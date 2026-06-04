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

function isApiEnvelope<T>(payload: unknown): payload is ApiEnvelope<T> {
  return typeof payload === "object" && payload !== null && "status" in payload;
}

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
}

async function apiFetch<T>(path: string, init: RequestInit): Promise<T> {
  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
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

  if (!isApiEnvelope<T>(payload) || payload.status !== "ok") {
    throw new ApiError("Unexpected API response", res.status, payload);
  }
  return payload.data;
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return apiFetch<T>(path, { ...init, method: "GET" });
}

export async function apiPost<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  return apiFetch<T>(path, {
    ...init,
    method: "POST",
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

export async function apiPut<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  return apiFetch<T>(path, {
    ...init,
    method: "PUT",
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

export async function apiDelete<T>(path: string, init?: RequestInit): Promise<T> {
  return apiFetch<T>(path, { ...init, method: "DELETE" });
}
