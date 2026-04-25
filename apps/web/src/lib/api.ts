// argus — typed fetch wrappers against the FastAPI backend.
// Falls back gracefully — callers using TanStack Query should treat errors as "use mock".

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export function wsUrl(discussionId: string): string {
  return `${WS_BASE}/ws/discussions/${discussionId}`;
}

export type HealthResponse = {
  status: string;
  version?: string;
};

// --- live schemas (mirror of argus_core.schemas) ---

export type ClaimStatus = "likely_true" | "contested" | "unverified" | "likely_false";

export type EvidenceRef = {
  source_id: string;
  verbatim_span: string;
  char_start: number;
  char_end: number;
  fetched_at: string;
  trust_tier: number;
};

export type AgentConsensus = {
  agree: number;
  disagree: number;
  uncertain: number;
};

export type Claim = {
  id: string;
  statement: string;
  status: ClaimStatus;
  confidence: number;
  supporting_evidence: EvidenceRef[];
  contradicting_evidence: EvidenceRef[];
  affected_entities: string[];
  agent_consensus: AgentConsensus;
  created_at: string;
  updated_at: string;
};

export type EntityType =
  | "person"
  | "org"
  | "place"
  | "event"
  | "policy"
  | "product"
  | "concept";

export type Entity = {
  id: string;
  canonical_name: string;
  entity_type: EntityType;
  wikidata_id: string | null;
  aliases: string[];
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type EntityRelation = {
  id: string;
  subject_id: string;
  relation_type: string;
  object_id: string;
  confidence: number;
  valid_from: string | null;
  valid_to: string | null;
  evidence: unknown[];
  created_at: string;
};

export type Source = {
  id: string;
  url: string | null;
  feed_url: string | null;
  title: string;
  content_hash: string;
  raw_text: string;
  fetched_at: string;
  published_at: string | null;
  license: string | null;
  trust_tier: number;
  publisher: string | null;
  language: string | null;
};

export type DiscussionStatus =
  | "planning"
  | "researching"
  | "debating"
  | "synthesizing"
  | "completed"
  | "failed";

export type AgentRole = "research" | "master" | "persona" | "critic" | "synthesizer";

export type AgentMessage = {
  id: string;
  discussion_id: string;
  agent_id: string;
  persona_id: string | null;
  role: AgentRole;
  content: string;
  evidence_refs: EvidenceRef[];
  parent_message_id: string | null;
  created_at: string;
};

export type DiscussionRun = {
  id: string;
  topic: string;
  vertical: string;
  status: DiscussionStatus;
  messages_count: number;
  final_claim_ids: string[];
  error: string | null;
};

export type CreateDiscussionResponse = {
  discussion_id: string;
  workflow_id: string;
};

// --- legacy / lightweight summaries kept for any callers still using them ---

export type ClaimSummary = Claim;
export type EntitySummary = Entity;
export type SourceSummary = Source;
export type DiscussionSummary = DiscussionRun;

// --- request plumbing ---

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  );
  if (entries.length === 0) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of entries) sp.set(k, String(v));
  return `?${sp.toString()}`;
}

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

type ListOpts = { limit?: number; offset?: number };

export const api = {
  health: () => request<HealthResponse>("/health"),
  healthDb: () => request<HealthResponse>("/health/db"),

  claims: (opts: ListOpts & { status?: ClaimStatus } = {}) =>
    request<Claim[]>(`/claims${qs({ ...opts })}`),
  claim: (id: string) => request<Claim>(`/claims/${id}`),
  claimEvidence: (id: string) => request<EvidenceRef[]>(`/claims/${id}/evidence`),

  entities: (opts: ListOpts & { entity_type?: EntityType } = {}) =>
    request<Entity[]>(`/entities${qs({ ...opts })}`),
  entity: (id: string) => request<Entity>(`/entities/${id}`),
  entityRelations: (id: string, opts: ListOpts = {}) =>
    request<EntityRelation[]>(`/entities/${id}/relations${qs({ ...opts })}`),

  sources: (opts: ListOpts & { include_text?: boolean } = {}) =>
    request<Source[]>(`/sources${qs({ ...opts })}`),
  source: (id: string, opts: { include_text?: boolean } = {}) =>
    request<Source>(`/sources/${id}${qs({ ...opts })}`),

  discussions: (opts: ListOpts = {}) =>
    request<DiscussionRun[]>(`/discussions${qs({ ...opts })}`),
  discussion: (id: string) => request<DiscussionRun>(`/discussions/${id}`),
  discussionMessages: (id: string, opts: ListOpts = {}) =>
    request<AgentMessage[]>(`/discussions/${id}/messages${qs({ ...opts })}`),
  createDiscussion: (body: { topic: string; vertical: string }) =>
    request<CreateDiscussionResponse>("/discussions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
