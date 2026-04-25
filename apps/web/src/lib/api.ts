// argus — typed fetch wrappers against the FastAPI backend.
// Falls back gracefully — callers using TanStack Query should treat errors as "use mock".

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
  version?: string;
};

export type ClaimSummary = {
  id: string;
  text?: string;
  subject?: string;
  predicate?: string;
  object?: string;
  confidence?: number;
  created_at?: string;
  source_id?: string;
};

export type EntitySummary = {
  id: string;
  name?: string;
  type?: string;
  canonical_name?: string;
};

export type SourceSummary = {
  id: string;
  name?: string;
  type?: string;
  status?: string;
};

export type DiscussionSummary = {
  id: string;
  topic?: string;
  status?: string;
  created_at?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`api ${res.status}: ${path}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  healthDb: () => request<HealthResponse>("/health/db"),
  claims: () => request<ClaimSummary[]>("/claims"),
  claim: (id: string) => request<ClaimSummary>(`/claims/${id}`),
  claimEvidence: (id: string) => request<unknown[]>(`/claims/${id}/evidence`),
  entities: () => request<EntitySummary[]>("/entities"),
  entity: (id: string) => request<EntitySummary>(`/entities/${id}`),
  sources: () => request<SourceSummary[]>("/sources"),
  source: (id: string) => request<SourceSummary>(`/sources/${id}`),
  discussion: (id: string) => request<DiscussionSummary>(`/discussions/${id}`),
  discussionMessages: (id: string) => request<unknown[]>(`/discussions/${id}/messages`),
};
