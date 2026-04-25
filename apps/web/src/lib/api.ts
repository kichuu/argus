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

export type SourceStats = {
  total: number;
  last_24h: number;
  events_per_hour_24h: number;
  by_trust_tier: Record<string, number>;
  by_publisher_top10: { name: string; count: number }[];
  duplicates_blocked_24h_est: number | null;
  spark_24h: number[];
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
  temperature?: number;
  redlines?: string[];
  bias?: string | null;
  model_assignment?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type PersonaPatch = Partial<{
  frame: string;
  description: string;
  knowledge_emphasis: string[];
  temperature: number;
  redlines: string[];
  bias: string | null;
  model_assignment: string | null;
}>;

export type SuggestedTopic = { id: string; title: string; rationale?: string };
export type SuggestedTopicsResponse = {
  topics: SuggestedTopic[];
  generated_at: string;
  claim_basis_count: number;
  error?: string;
};

export type ConfigResponse = {
  vertical: string;
  models: Record<
    "synthesis" | "extractor" | "verifier" | "research" | "persona" | "master" | "critic",
    string
  >;
  ingest: {
    enabled: boolean;
    interval_seconds: number;
    max_items_per_feed: number;
    feeds_path: string;
  };
  qdrant: { collection: string };
  embedding_model: string;
  reranker_model: string;
};

export type MetricsOverview = {
  debates_24h: number;
  claims_24h: number;
  claims_total: number;
  sources_24h: number;
  sources_total: number;
  verified_rate: number | null;
  hallucination_rate: number | null;
  tok_24h_est: number;
  cost_24h_est_usd: number;
  err_rate: number | null;
  spark_debates: number[];
  spark_claims: number[];
  spark_cost: number[];
  spark_err: number[];
};

export type MetricsTraceRow = {
  id: string;
  label: string;
  model: string;
  tokens_est: number;
  cost_est_usd: number;
  latency_seconds: number | null;
  status: string;
};

export type MetricsTraces = {
  traces: MetricsTraceRow[];
};

export type MetricsEvals = {
  consensus_quality: number | null;
  citation_coverage: number | null;
  persona_drift: number | null;
  synth_faithfulness: number | null;
  hallucination_rate: number | null;
  n_gold: number | null;
  last_run: string | null;
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
  sourceStats: () => request<SourceStats>("/sources/stats"),
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
  startDiscussion: (body: {
    topic: string;
    vertical?: string;
    depth?: "quick" | "standard" | "deep";
    source_kinds?: ("rss" | "news" | "social" | "kg")[];
    auto_personas?: boolean;
  }) =>
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
    temperature?: number;
    redlines?: string[];
    bias?: string | null;
    model_assignment?: string | null;
  }) =>
    request<PersonaSummary>("/personas", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updatePersona: (id: string, patch: PersonaPatch) =>
    request<PersonaSummary>(`/personas/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deletePersona: (id: string) =>
    request<void>(`/personas/${id}`, { method: "DELETE" }),
  config: () => request<ConfigResponse>("/config"),
  suggestedTopics: (opts?: { limit?: number; force?: boolean }) => {
    const params = new URLSearchParams();
    if (opts?.limit != null) params.set("limit", String(opts.limit));
    if (opts?.force) params.set("force", "true");
    const qs = params.toString();
    return request<SuggestedTopicsResponse>(
      `/suggested-topics${qs ? `?${qs}` : ""}`,
    );
  },
  metricsOverview: () => request<MetricsOverview>("/metrics/overview"),
  metricsTraces: (opts?: { limit?: number }) => {
    const qs = opts?.limit != null ? `?limit=${opts.limit}` : "";
    return request<MetricsTraces>(`/metrics/traces${qs}`);
  },
  metricsEvals: () => request<MetricsEvals>("/metrics/evals"),
};
