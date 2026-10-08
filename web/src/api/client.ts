import i18n from "@/i18n";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export class ApiError extends Error {
  status: number;
  data: Record<string, string | number | boolean | null> | null;

  constructor(message: string, status: number, data?: Record<string, string | number | boolean | null> | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data ?? null;
  }
}

function getUsername(): string {
  return localStorage.getItem("username") || "";
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const username = getUsername();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept-Language": i18n.language || "en",
    ...(username ? { "X-Username": username } : {}),
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      (data as { error?: string })?.error || `HTTP ${response.status}`;
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

export function apiGet<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: "GET" });
}

type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export function apiPost<T>(endpoint: string, body?: JsonValue): Promise<T> {
  return request<T>(endpoint, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

export function apiPut<T>(endpoint: string, body?: JsonValue): Promise<T> {
  return request<T>(endpoint, {
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  });
}

export function apiDelete<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: "DELETE" });
}
