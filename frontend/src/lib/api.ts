/** API client for the Agentic Developer backend. */

import type {
  HealthResponse,
  IndexRequest,
  IndexResponse,
  PaginatedTasks,
  SearchRequest,
  SearchResponse,
  TaskCreate,
  TaskDetail,
  TaskResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Health ──

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

// ── Tasks ──

export function createTask(body: TaskCreate): Promise<TaskResponse> {
  return request<TaskResponse>("/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listTasks(
  page = 1,
  perPage = 20,
  status?: string,
): Promise<PaginatedTasks> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  if (status) params.set("status", status);
  return request<PaginatedTasks>(`/tasks?${params}`);
}

export function getTask(taskId: string): Promise<TaskDetail> {
  return request<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}`);
}

export function cancelTask(taskId: string): Promise<TaskResponse> {
  return request<TaskResponse>(`/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
  });
}

// ── Index ──

export function indexProject(body: IndexRequest): Promise<IndexResponse> {
  return request<IndexResponse>("/index", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Search ──

export function searchCode(body: SearchRequest): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── WebSocket ──

export function taskWebSocketUrl(taskId: string): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/ws/tasks/${encodeURIComponent(taskId)}`;
}
