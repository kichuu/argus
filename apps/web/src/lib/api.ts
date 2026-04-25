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
  vertical?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  evidence_count?: number;
  claim_count?: number;
};

export type SourceIngestResponse = {
  id: string;
  title: string;
  content_hash: string;
  chars: number;
  status: "ingested" | "duplicate";
  trust_tier?: number | null;
};

export type DiscussionMessage = {
  id?: string;
  agent_id?: string;
  role?: string;
  content?: string;
  evidence_refs?: unknown[];
  persona_id?: string;
  created_at?: string;
};

export type RelationSummary = {
  id: string;
  subject_id: string;
  relation_type: string;
  object_id: string;
  confidence?: number;
  valid_from?: string | null;
  valid_to?: string | null;
};

export type PersonaSummary = {
  id: string;
  frame: string;
  description: string;
  knowledge_emphasis: string[];
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
  if (res.status === 204) {
    return undefined as T;
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
  ingestSource: (body: { url: string }) =>
    request<SourceIngestResponse>("/sources", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  discussions: () => request<DiscussionSummary[]>("/discussions"),
  discussion: (id: string) => request<DiscussionSummary>(`/discussions/${id}`),
  discussionMessages: (id: string) =>
    request<DiscussionMessage[]>(`/discussions/${id}/messages`),
  discussionClaims: (id: string) =>
    request<ClaimSummary[]>(`/discussions/${id}/claims`),
  startDiscussion: (body: { topic: string; vertical?: string }) =>
    request<{ id: string; status: string }>("/discussions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  entityRelations: (id: string) =>
    request<RelationSummary[]>(`/entities/${id}/relations`),
  personas: () => request<PersonaSummary[]>("/personas"),
  persona: (id: string) => request<PersonaSummary>(`/personas/${id}`),
  createPersona: (body: {
    frame: string;
    description: string;
    knowledge_emphasis: string[];
  }) =>
    request<PersonaSummary>("/personas", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deletePersona: (id: string) =>
    request<void>(`/personas/${id}`, { method: "DELETE" }),
};
