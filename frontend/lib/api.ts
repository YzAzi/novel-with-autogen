import type { APIResponse, ExpandChapterResult, ProjectState, RagPreview, RagStats } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<APIResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) }
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as APIResponse<T>;
}

export const api = {
  createProject: (payload: {
    genre: string;
    setting?: string;
    style?: string;
    keywords?: string;
    audience?: string;
    target_chapters?: number;
  }) => request<ProjectState>("/projects", { method: "POST", body: JSON.stringify(payload) }),

  getProject: (id: string) => request<ProjectState>(`/projects/${id}`),

  generateOutline: (id: string, payload: { theme?: string; total_words?: number }) =>
    request<ProjectState>(`/projects/${id}/outline`, { method: "POST", body: JSON.stringify(payload) }),

  generateCharacters: (id: string, payload: { constraints?: string }) =>
    request<ProjectState>(`/projects/${id}/characters`, { method: "POST", body: JSON.stringify(payload) }),

  expandChapter: (id: string, n: number, payload: { instruction?: string; target_words?: number }) =>
    request<ExpandChapterResult>(`/projects/${id}/chapters/${n}/expand`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  ragStats: (id: string) => request<RagStats>(`/projects/${id}/rag/stats`),

  ragPreview: (id: string, params: { chapter?: number; query?: string; top_k?: number }) => {
    const usp = new URLSearchParams();
    if (params.chapter) usp.set("chapter", String(params.chapter));
    if (params.query) usp.set("query", params.query);
    if (params.top_k) usp.set("top_k", String(params.top_k));
    return request<RagPreview>(`/projects/${id}/rag/preview?${usp.toString()}`);
  }
};
