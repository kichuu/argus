"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { AsciiSpinner } from "@/components/ui/AsciiSpinner";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { useQuery } from "@tanstack/react-query";
import { useDiscussionStream, type StreamMode } from "@/hooks/useDiscussionStream";
import {
  api,
  type AgentMessage,
  type Claim,
  type DiscussionStatus as DStatus,
  type EvidenceRef,
  type Source,
} from "@/lib/api";
import { useDebateStore } from "@/store/debate";

const TERMINAL: DStatus[] = ["completed", "failed"];

const VERTICALS = [
  { value: "geopolitics", label: "GEO" },
  { value: "macro", label: "MACRO" },
  { value: "tech", label: "TECH" },
  { value: "policy", label: "POLICY" },
  { value: "general", label: "GEN" },
] as const;

const STATUS_TONE: Record<DStatus, "amber" | "green" | "red"> = {
  planning: "amber",
  researching: "amber",
  debating: "amber",
  criticizing: "amber",
  synthesizing: "amber",
  completed: "green",
  failed: "red",
};

// FNV-ish hash for deterministic color cycling per persona/agent.
function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = (h * 16777619) >>> 0;
  }
  return h;
}

function colorFor(key: string): string {
  // 7 persona accent tokens; cycle by hash.
  return `var(--p-${(hash(key) % 7) + 1})`;
}

function initialsFor(key: string): string {
  const cleaned = key.replace(/[_-]/g, " ").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return key.slice(0, 2).toUpperCase();
}

function relTime(iso: string): string {
  const d = new Date(iso);
  const ms = Date.now() - d.getTime();
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

const _EV_RE = /\[ev:([0-9a-fA-F-]{36})\]/g;

// Convert raw [ev:UUID] markers in agent text into compact superscript [N]
// chips that map to the message's evidence_refs index. Long citation chains
// would otherwise render as wall-of-text garbage.
function renderContent(content: string, refs: AgentMessage["evidence_refs"]): React.ReactNode {
  if (!content) return null;
  const idIndex = new Map<string, number>();
  refs.forEach((r, i) => idIndex.set(String(r.source_id).toLowerCase(), i + 1));
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  const re = new RegExp(_EV_RE.source, "g");
  while ((m = re.exec(content)) !== null) {
    if (m.index > last) parts.push(<span key={key++}>{content.slice(last, m.index)}</span>);
    const id = m[1].toLowerCase();
    const n = idIndex.get(id);
    const ref = n ? refs[n - 1] : undefined;
    parts.push(
      <span
        key={key++}
        title={ref?.verbatim_span ?? id}
        style={{
          display: "inline-block",
          fontSize: 9,
          color: "var(--amber)",
          border: "1px solid var(--amber-dim)",
          padding: "0 3px",
          margin: "0 1px",
          verticalAlign: "super",
          lineHeight: 1.2,
          cursor: "help",
        }}
      >
        {n ?? "?"}
      </span>,
    );
    last = m.index + m[0].length;
  }
  if (last < content.length) parts.push(<span key={key++}>{content.slice(last)}</span>);
  const textOnly = content.replace(_EV_RE, "").trim();
  if (!textOnly) {
    return (
      <span style={{ color: "var(--ink-3)", fontStyle: "italic" }}>
        [no narrative — only citations: {refs.length}]
      </span>
    );
  }
  return <>{parts}</>;
}

// Lazy-fetches one Source by id (cached + dedupped via react-query) and
// renders a single row showing publisher · domain · title · trust + the
// cited verbatim span. Used by EvidenceList below.
function SourceRefRow({
  index,
  ref,
}: {
  index: number;
  ref: EvidenceRef;
}) {
  const q = useQuery<Source>({
    queryKey: ["source", ref.source_id],
    queryFn: () => api.source(ref.source_id, { include_text: false }),
    staleTime: 5 * 60_000,
    retry: 0,
  });
  const src = q.data;
  const host = (() => {
    try {
      return src?.url ? new URL(src.url).hostname.replace(/^www\./, "") : "";
    } catch {
      return "";
    }
  })();
  return (
    <div
      style={{
        padding: "8px 10px",
        borderTop: "1px solid var(--line-1)",
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
      }}
    >
      <span
        className="tab"
        style={{
          fontSize: 9,
          color: "var(--ink-2)",
          minWidth: 18,
          textAlign: "right",
          marginTop: 1,
        }}
      >
        [{index}]
      </span>
      <span
        className="tt-up"
        style={{
          fontSize: 9,
          color: "var(--ink-1)",
          border: "1px solid var(--line-2)",
          padding: "0 4px",
          marginTop: 1,
        }}
      >
        T{ref.trust_tier}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        {q.isLoading && (
          <span style={{ fontSize: 11, color: "var(--ink-3)" }}>loading source…</span>
        )}
        {q.isError && (
          <span style={{ fontSize: 11, color: "var(--red)" }}>
            source {ref.source_id.slice(0, 8)} unavailable
          </span>
        )}
        {src && (
          <>
            <div className="row gap-2" style={{ alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, color: "var(--ink-0)", fontWeight: 500 }}>
                {src.title || "(untitled)"}
              </span>
              {host && (
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  {host}
                </span>
              )}
              {src.publisher && (
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  · {src.publisher}
                </span>
              )}
              {src.url && (
                <a
                  href={src.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="tt-up"
                  style={{
                    fontSize: 9,
                    color: "var(--amber)",
                    textDecoration: "none",
                    border: "1px solid var(--amber-dim)",
                    padding: "0 5px",
                    marginLeft: "auto",
                  }}
                >
                  ↗ open
                </a>
              )}
            </div>
            <div
              style={{
                fontSize: 10,
                color: "var(--ink-2)",
                marginTop: 4,
                fontStyle: "italic",
                lineHeight: 1.45,
                fontFamily: "'IBM Plex Sans', 'Inter', system-ui, sans-serif",
              }}
            >
              &ldquo;{ref.verbatim_span}&rdquo;
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function EvidenceList({
  refs,
  label,
  defaultOpen = false,
}: {
  refs: EvidenceRef[];
  label: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  if (refs.length === 0) return null;
  return (
    <div style={{ marginTop: 8, border: "1px solid var(--line-1)" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          all: "unset",
          width: "100%",
          padding: "6px 10px",
          background: open ? "var(--bg-3)" : "var(--bg-2)",
          fontFamily: "inherit",
          cursor: "pointer",
          display: "flex",
          gap: 6,
          alignItems: "center",
        }}
      >
        <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
          {open ? "−" : "+"} {label}
        </span>
        <span className="tab" style={{ fontSize: 9, color: "var(--ink-3)" }}>
          {refs.length}
        </span>
      </button>
      {open && (
        <div>
          {refs.map((r, i) => (
            <SourceRefRow key={`${r.source_id}-${i}`} index={i + 1} ref={r} />
          ))}
        </div>
      )}
    </div>
  );
}

function MessageRow({ m }: { m: AgentMessage }) {
  const key = m.persona_id ?? m.agent_id ?? m.role;
  const color = colorFor(key);
  const initials = initialsFor(key);
  const t = new Date(m.created_at);
  const tStr = `${String(t.getUTCHours()).padStart(2, "0")}:${String(t.getUTCMinutes()).padStart(2, "0")}:${String(t.getUTCSeconds()).padStart(2, "0")}`;
  const isCritic = m.role === "critic";
  const [expanded, setExpanded] = useState(!isCritic);
  const refsToShow = m.evidence_refs.slice(0, 8);
  const refsHidden = Math.max(0, m.evidence_refs.length - 8);
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line-1)" }}>
      <div className="row gap-3" style={{ alignItems: "flex-start" }}>
        <div
          style={{
            width: 28,
            height: 28,
            border: `1px solid ${color}`,
            color,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            fontWeight: 600,
            flexShrink: 0,
            background: "var(--bg-2)",
          }}
        >
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row gap-2" style={{ alignItems: "baseline", flexWrap: "wrap" }}>
            <span style={{ color, fontWeight: 600, fontSize: 12 }}>{m.agent_id}</span>
            <span className="tt-up muted" style={{ fontSize: 9 }}>
              {m.role}
            </span>
            <div style={{ flex: 1 }} />
            <span className="tab muted" style={{ fontSize: 9 }}>
              {tStr}
            </span>
          </div>
          <div
            style={{
              fontSize: 13,
              color: "var(--ink-0)",
              marginTop: 6,
              lineHeight: 1.55,
              fontFamily: "'IBM Plex Sans', 'Inter', system-ui, sans-serif",
              whiteSpace: "pre-wrap",
              maxHeight: expanded ? undefined : 120,
              overflow: expanded ? undefined : "hidden",
              position: "relative",
            }}
          >
            {renderContent(m.content, m.evidence_refs)}
          </div>
          {(isCritic || m.content.length > 600) && (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="tt-up muted"
              style={{
                marginTop: 4,
                fontSize: 9,
                background: "transparent",
                border: "none",
                color: "var(--ink-2)",
                cursor: "pointer",
                fontFamily: "inherit",
                padding: 0,
              }}
            >
              {expanded ? "− collapse" : "+ expand"}
            </button>
          )}
          {refsToShow.length > 0 && (
            <div className="row gap-1" style={{ flexWrap: "wrap", marginTop: 8 }}>
              {refsToShow.map((e, i) => (
                <span
                  key={i}
                  title={`${e.verbatim_span}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 3,
                    border: "1px solid var(--line-2)",
                    background: "var(--bg-3)",
                    padding: "0 4px",
                    fontSize: 9,
                    color: "var(--amber)",
                  }}
                >
                  <span style={{ color: "var(--ink-2)" }}>[{i + 1}]</span>
                  <span className="tt-up" style={{ color: "var(--ink-1)" }}>
                    T{e.trust_tier}
                  </span>
                </span>
              ))}
              {refsHidden > 0 && (
                <span
                  style={{
                    fontSize: 9,
                    color: "var(--ink-2)",
                    padding: "0 4px",
                    border: "1px dashed var(--line-2)",
                  }}
                >
                  +{refsHidden} more
                </span>
              )}
            </div>
          )}
          {m.evidence_refs.length > 0 && (
            <EvidenceList refs={m.evidence_refs} label="sources cited by this agent" />
          )}
        </div>
      </div>
    </div>
  );
}

type CastSelection = string | "__synthesis__" | "__all__" | null;

function CastPanel({
  messages,
  claimCount,
  selected,
  onSelect,
}: {
  messages: AgentMessage[];
  claimCount: number;
  selected: CastSelection;
  onSelect: (key: CastSelection) => void;
}) {
  const groups = useMemo(() => {
    const map = new Map<
      string,
      { key: string; agent: string; role: string; count: number; last: string }
    >();
    for (const m of messages) {
      const key = m.persona_id ?? m.agent_id ?? m.role;
      const existing = map.get(key);
      if (existing) {
        existing.count += 1;
        existing.last = m.created_at;
      } else {
        map.set(key, {
          key,
          agent: m.agent_id,
          role: m.role,
          count: 1,
          last: m.created_at,
        });
      }
    }
    return Array.from(map.values());
  }, [messages]);

  const VirtualEntry = ({
    selKey,
    label,
    sub,
    icon,
  }: {
    selKey: CastSelection;
    label: string;
    sub: string;
    icon: string;
  }) => {
    const active = selected === selKey;
    return (
      <button
        type="button"
        onClick={() => onSelect(selKey)}
        style={{
          all: "unset",
          padding: "10px 12px",
          borderBottom: "1px solid var(--line-1)",
          display: "flex",
          gap: 8,
          alignItems: "center",
          borderLeft: `2px solid ${active ? "var(--amber)" : "transparent"}`,
          background: active ? "var(--bg-3)" : "transparent",
          cursor: "pointer",
          fontFamily: "inherit",
        }}
      >
        <div
          style={{
            width: 26,
            height: 26,
            border: "1px solid var(--line-2)",
            color: active ? "var(--amber)" : "var(--ink-1)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            background: "var(--bg-2)",
          }}
        >
          {icon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 11,
              color: active ? "var(--amber)" : "var(--ink-0)",
              fontWeight: active ? 600 : 400,
            }}
          >
            {label}
          </div>
          <div style={{ fontSize: 9, color: "var(--ink-2)" }}>{sub}</div>
        </div>
      </button>
    );
  };

  return (
    <div className="col" style={{ overflowY: "auto" }}>
      <VirtualEntry
        selKey="__synthesis__"
        label="Synthesis"
        sub={`${claimCount} claim${claimCount === 1 ? "" : "s"}`}
        icon="◆"
      />
      <VirtualEntry
        selKey="__all__"
        label="All Debate"
        sub={`${messages.length} message${messages.length === 1 ? "" : "s"}`}
        icon="≡"
      />
      {groups.length === 0 ? (
        <div style={{ padding: "12px 14px", fontSize: 11, color: "var(--ink-3)" }}>
          ── awaiting cast ──
        </div>
      ) : (
        groups.map((g) => {
          const color = colorFor(g.key);
          const active = selected === g.key;
          return (
            <button
              type="button"
              key={g.key}
              onClick={() => onSelect(g.key)}
              style={{
                all: "unset",
                padding: "10px 12px",
                borderBottom: "1px solid var(--line-1)",
                display: "flex",
                gap: 8,
                alignItems: "center",
                borderLeft: `2px solid ${color}`,
                background: active ? "var(--bg-3)" : "transparent",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              <div
                style={{
                  width: 26,
                  height: 26,
                  border: `1px solid ${color}`,
                  color,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  fontWeight: 600,
                  background: "var(--bg-2)",
                }}
              >
                {initialsFor(g.key)}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 11,
                    color: active ? "var(--amber)" : "var(--ink-0)",
                    fontWeight: active ? 600 : 400,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {g.agent}
                </div>
                <div style={{ fontSize: 9, color: "var(--ink-2)" }}>
                  {g.role} · {g.count} msg{g.count === 1 ? "" : "s"} · {relTime(g.last)}
                </div>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
}

function StatusPill({ s }: { s: DStatus }) {
  const tone = STATUS_TONE[s];
  const pulse = !TERMINAL.includes(s);
  return (
    <Chip tone={tone}>
      <Dot tone={tone} pulse={pulse} /> {s.toUpperCase()}
    </Chip>
  );
}

function ModeIndicator({ mode }: { mode: StreamMode }) {
  const tone = mode === "ws" ? "green" : "amber";
  const label = mode === "ws" ? "LIVE" : "POLL";
  return (
    <Chip tone={tone}>
      <Dot tone={tone} pulse={mode === "ws"} /> {label}
    </Chip>
  );
}

// =====================================================================
//  OrchestrationStrip — visual flow diagram of the council pipeline.
// =====================================================================

type BoxStatus = "queued" | "thinking" | "done" | "failed";

const PHASE_ORDER: DStatus[] = [
  "planning",
  "researching",
  "debating",
  "criticizing",
  "synthesizing",
  "completed",
];

function boxStatus(boxPhase: DStatus, current: DStatus | null): BoxStatus {
  if (current === "failed") return "failed";
  if (!current) return "queued";
  if (current === "completed") return "done";
  const ci = PHASE_ORDER.indexOf(current);
  const bi = PHASE_ORDER.indexOf(boxPhase);
  if (ci > bi) return "done";
  if (ci === bi) return "thinking";
  return "queued";
}

function FlowBox({
  label,
  status,
  accent,
  sub,
}: {
  label: string;
  status: BoxStatus;
  accent: string; // CSS var like "--p-1"
  sub?: string;
}) {
  const isThinking = status === "thinking";
  const isDone = status === "done";
  const isFailed = status === "failed";
  const borderColor =
    isFailed ? "var(--red)" : isDone || isThinking ? `var(${accent})` : "var(--line-2)";
  const textColor =
    isFailed ? "var(--red)" : isThinking ? `var(${accent})` : isDone ? "var(--ink-0)" : "var(--ink-3)";
  const bg =
    isThinking ? "var(--bg-3)" : isDone ? "var(--bg-2)" : isFailed ? "var(--bg-2)" : "var(--bg-1)";
  return (
    <div
      style={{
        width: 110,
        minHeight: 64,
        border: `1px solid ${borderColor}`,
        background: bg,
        padding: "8px 10px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        position: "relative",
        animation: isThinking ? "pulse-soft 1.6s ease-in-out infinite" : undefined,
        boxShadow: isThinking ? `0 0 12px var(${accent}-glow, rgba(245,165,36,0.18))` : undefined,
        flexShrink: 0,
      }}
    >
      <div
        className="tt-up"
        style={{ fontSize: 9, color: textColor, fontWeight: 600, letterSpacing: "0.08em" }}
      >
        {label}
      </div>
      <div className="row gap-1" style={{ alignItems: "center" }}>
        {isThinking && <Dot tone="amber" pulse size={6} />}
        {isDone && <Dot tone="green" size={6} />}
        {isFailed && <Dot tone="red" pulse size={6} />}
        {status === "queued" && <Dot tone="ink" size={6} />}
        <span
          className="tt-up"
          style={{ fontSize: 9, color: "var(--ink-2)", letterSpacing: "0.08em" }}
        >
          {isFailed ? "failed" : status}
        </span>
      </div>
      {sub && (
        <div
          className="tab"
          style={{ fontSize: 10, color: "var(--ink-1)", marginTop: "auto" }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function FlowArrow({ active }: { active: boolean }) {
  return (
    <div
      style={{
        flex: "0 0 28px",
        height: 2,
        background: active ? "var(--amber)" : "var(--line-2)",
        position: "relative",
        marginTop: 30,
        transition: "background 0.3s ease",
      }}
    >
      <span
        style={{
          position: "absolute",
          right: -4,
          top: -6,
          color: active ? "var(--amber)" : "var(--line-3)",
          fontSize: 12,
          lineHeight: 1,
          fontFamily: "monospace",
        }}
      >
        ▸
      </span>
    </div>
  );
}

function OrchestrationStrip({
  phase,
  messages,
  agentStatuses,
}: {
  phase: DStatus | null;
  messages: AgentMessage[];
  agentStatuses: Record<string, { state: string; extra: Record<string, unknown> }>;
}) {
  const personaTotal = useMemo(() => {
    const fromMaster = (agentStatuses["master"]?.extra?.["n_personas"] as number | undefined) ?? 0;
    if (fromMaster) return fromMaster;
    return new Set(messages.filter((m) => m.role === "persona").map((m) => m.persona_id ?? m.agent_id)).size;
  }, [messages, agentStatuses]);
  const personaDone = useMemo(
    () => new Set(messages.filter((m) => m.role === "persona").map((m) => m.persona_id ?? m.agent_id)).size,
    [messages],
  );
  const research = boxStatus("researching", phase);
  const master = boxStatus("planning", phase);
  const personas = boxStatus("debating", phase);
  const critic = boxStatus("criticizing", phase);
  const synth = boxStatus("synthesizing", phase);
  const completed = phase === "completed";

  return (
    <div
      style={{
        padding: "12px 14px",
        borderBottom: "1px solid var(--line-2)",
        background: "var(--bg-1)",
        display: "flex",
        alignItems: "flex-start",
        gap: 0,
        overflowX: "auto",
        flexShrink: 0,
      }}
    >
      <FlowBox label="RESEARCH" status={research} accent="--p-2" sub="evidence pack" />
      <FlowArrow active={research === "done"} />
      <FlowBox label="MASTER" status={master} accent="--p-1" sub={personaTotal > 0 ? `${personaTotal} personas` : undefined} />
      <FlowArrow active={master === "done"} />
      <FlowBox
        label="PERSONAS"
        status={personas}
        accent="--p-4"
        sub={personaTotal > 0 ? `${personaDone}/${personaTotal} done` : "—"}
      />
      <FlowArrow active={personas === "done"} />
      <FlowBox label="CRITIC" status={critic} accent="--p-5" sub="audit citations" />
      <FlowArrow active={critic === "done"} />
      <FlowBox
        label="SYNTH"
        status={synth}
        accent="--p-3"
        sub={completed ? "claims emitted" : "structured claims"}
      />
    </div>
  );
}

function CenterView({
  transcriptRef,
  discussionId,
  topic,
  messageList,
  stream,
  sStatus,
  hasStatus,
  isTerminal,
  failed,
  castSelection,
  onSelect,
}: {
  transcriptRef: React.RefObject<HTMLDivElement | null>;
  discussionId: string | null;
  topic: string;
  messageList: AgentMessage[];
  stream: ReturnType<typeof useDiscussionStream>;
  sStatus: DStatus;
  hasStatus: boolean;
  isTerminal: boolean;
  failed: boolean;
  castSelection: CastSelection;
  onSelect: (key: CastSelection) => void;
}) {
  // Resolve effective view: explicit cast pick -> if null, default to
  // synthesis when terminal, all-debate while running.
  const effective: CastSelection =
    castSelection ??
    (isTerminal && stream.claims.length > 0 ? "__synthesis__" : "__all__");

  const filteredMessages = useMemo(() => {
    if (effective === "__all__" || effective === "__synthesis__") return messageList;
    return messageList.filter(
      (m) => (m.persona_id ?? m.agent_id ?? m.role) === effective,
    );
  }, [effective, messageList]);

  const headerLabel =
    effective === "__synthesis__"
      ? "SYNTHESIS"
      : effective === "__all__"
        ? "ALL DEBATE"
        : `AGENT · ${filteredMessages[0]?.agent_id ?? "—"}`;

  const sub =
    effective === "__synthesis__"
      ? `${stream.claims.length} claim${stream.claims.length === 1 ? "" : "s"}`
      : `${filteredMessages.length} msg${filteredMessages.length === 1 ? "" : "s"}`;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      {discussionId && (
        <OrchestrationStrip
          phase={stream.phase}
          messages={messageList}
          agentStatuses={stream.agentStatuses}
        />
      )}
      <div
        className="row"
        style={{
          padding: "8px 14px",
          borderBottom: "1px solid var(--line-2)",
          background: "var(--bg-1)",
          alignItems: "center",
          gap: 10,
          flexShrink: 0,
        }}
      >
        <span className="tt-up amber" style={{ fontSize: 10, fontWeight: 600 }}>
          {headerLabel}
        </span>
        <span className="muted tt-up" style={{ fontSize: 9 }}>
          {sub}
        </span>
        <div style={{ flex: 1 }} />
        {castSelection !== null && (
          <button
            type="button"
            onClick={() => onSelect(null)}
            className="tt-up"
            style={{
              all: "unset",
              fontSize: 9,
              padding: "3px 8px",
              border: "1px solid var(--line-2)",
              cursor: "pointer",
              color: "var(--ink-1)",
              background: "transparent",
            }}
          >
            ← back to default
          </button>
        )}
      </div>
      <div ref={transcriptRef} className="grow" style={{ overflowY: "auto", padding: "12px 0" }}>
        {!discussionId && (
          <div
            style={{
              padding: 32,
              textAlign: "center",
              color: "var(--ink-2)",
              fontSize: 12,
            }}
          >
            ── enter a topic and hit RUN to convene the council ──
          </div>
        )}
        {discussionId && effective === "__synthesis__" && (
          <SynthesisPanel claims={stream.claims} topic={topic} />
        )}
        {discussionId && effective !== "__synthesis__" && filteredMessages.length === 0 && hasStatus && (
          <div style={{ padding: 24, color: "var(--ink-3)", fontSize: 11, textAlign: "center" }}>
            ── no messages from this agent yet ──
          </div>
        )}
        {discussionId &&
          effective !== "__synthesis__" &&
          filteredMessages.map((m) => <MessageRow key={m.id} m={m} />)}
        {discussionId && hasStatus && !isTerminal && effective !== "__synthesis__" && (
          <div style={{ padding: "8px 16px", fontSize: 10, color: "var(--ink-3)" }}>
            <AsciiSpinner /> {sStatus}...
          </div>
        )}
        {failed && (
          <div
            style={{
              padding: 24,
              margin: 16,
              border: "1px solid var(--red-dim)",
              background: "var(--bg-2)",
              fontSize: 11,
              color: "var(--red)",
            }}
          >
            ── debate failed ──
            {stream.errorDetail && (
              <div style={{ marginTop: 8, color: "var(--ink-1)", fontFamily: "inherit" }}>
                {stream.errorDetail}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function VerdictCard({ topic, claims }: { topic: string; claims: Claim[] }) {
  const counts = { likely_true: 0, contested: 0, unverified: 0, likely_false: 0 };
  let totalConf = 0;
  let totalEvidence = 0;
  const seenEv = new Set<string>();
  for (const c of claims) {
    counts[c.status] += 1;
    totalConf += c.confidence;
    for (const e of c.supporting_evidence) {
      seenEv.add(e.source_id);
    }
  }
  totalEvidence = seenEv.size;
  const avgConf = claims.length > 0 ? totalConf / claims.length : 0;

  // Headline: synthesizer is prompted to put the topic answer FIRST. Use
  // claim[0] when present; fall back to highest-confidence likely_true; then
  // highest-confidence overall.
  const sorted = [...claims].sort((a, b) => b.confidence - a.confidence);
  const headline =
    claims[0] ?? sorted.find((c) => c.status === "likely_true") ?? sorted[0];

  // If every claim sits at exactly 0.5, the synthesizer hit the critic-cap.
  const allCapped =
    claims.length > 0 && claims.every((c) => Math.abs(c.confidence - 0.5) < 0.001);

  let verdictTone: "green" | "amber" | "red" | "default" = "default";
  let verdictLabel = "INCONCLUSIVE";
  if (counts.likely_false > 0 && counts.likely_true === 0) {
    verdictTone = "red";
    verdictLabel = "REFUTED";
  } else if (counts.contested > 0) {
    verdictTone = "amber";
    verdictLabel = "CONTESTED";
  } else if (counts.likely_true > 0 && counts.unverified === 0) {
    verdictTone = "green";
    verdictLabel = "VERIFIED";
  } else if (counts.likely_true > 0) {
    verdictTone = "amber";
    verdictLabel = "PARTIAL SUPPORT";
  } else if (counts.unverified > 0) {
    verdictTone = "default";
    verdictLabel = "UNVERIFIED";
  }

  const verdictColor =
    verdictTone === "green"
      ? "var(--green)"
      : verdictTone === "amber"
        ? "var(--amber)"
        : verdictTone === "red"
          ? "var(--red)"
          : "var(--ink-2)";

  return (
    <div
      style={{
        padding: 14,
        borderBottom: "1px solid var(--line-2)",
        background: "var(--bg-2)",
      }}
    >
      <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 4 }}>
        TOPIC
      </div>
      <div
        style={{
          fontSize: 12,
          color: "var(--ink-1)",
          marginBottom: 12,
          fontStyle: "italic",
          lineHeight: 1.4,
        }}
      >
        {topic || "(no topic)"}
      </div>

      <div className="row gap-2" style={{ alignItems: "baseline", marginBottom: 8 }}>
        <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
          VERDICT
        </span>
        <Chip tone={verdictTone}>
          <Dot tone={verdictTone === "default" ? "ink" : verdictTone} size={6} />
          {verdictLabel}
        </Chip>
        <div style={{ flex: 1 }} />
        <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
          AGG CONF
        </span>
        <Bar value={avgConf} width={60} color={verdictColor} showVal />
      </div>

      {headline && (
        <div
          style={{
            padding: "8px 10px",
            border: `1px solid ${verdictColor}`,
            background: "var(--bg-1)",
            fontSize: 13,
            color: "var(--ink-0)",
            lineHeight: 1.5,
            marginBottom: 10,
          }}
        >
          <div className="tt-up" style={{ fontSize: 9, color: verdictColor, marginBottom: 4 }}>
            ▸ HEADLINE
          </div>
          {headline.statement}
        </div>
      )}

      <div className="row gap-3" style={{ flexWrap: "wrap", fontSize: 10 }}>
        <span className="muted">
          <span className="tab" style={{ color: "var(--ink-0)" }}>
            {claims.length}
          </span>{" "}
          claims
        </span>
        <span className="muted">
          <span className="tab" style={{ color: "var(--ink-0)" }}>
            {totalEvidence}
          </span>{" "}
          unique sources
        </span>
        {counts.likely_true > 0 && (
          <span style={{ color: "var(--green)" }}>
            <span className="tab">{counts.likely_true}</span> true
          </span>
        )}
        {counts.contested > 0 && (
          <span style={{ color: "var(--amber)" }}>
            <span className="tab">{counts.contested}</span> contested
          </span>
        )}
        {counts.unverified > 0 && (
          <span style={{ color: "var(--ink-2)" }}>
            <span className="tab">{counts.unverified}</span> unverified
          </span>
        )}
        {counts.likely_false > 0 && (
          <span style={{ color: "var(--red)" }}>
            <span className="tab">{counts.likely_false}</span> false
          </span>
        )}
      </div>

      {allCapped && (
        <div
          style={{
            marginTop: 10,
            padding: "6px 8px",
            fontSize: 10,
            color: "var(--ink-2)",
            border: "1px dashed var(--line-2)",
            background: "var(--bg-3)",
          }}
        >
          ✕ confidence critic-capped at 0.5 — persona narrative was thin; the
          synthesizer couldn&apos;t cross-check assertions against the cited spans.
        </div>
      )}
    </div>
  );
}

function SynthesisPanel({ claims, topic }: { claims: Claim[]; topic: string }) {
  return (
    <div className="col" style={{ overflowY: "auto" }}>
      {claims.length > 0 && <VerdictCard topic={topic} claims={claims} />}
      {claims.length === 0 && (
        <div style={{ padding: 14, fontSize: 11, color: "var(--ink-3)" }}>
          synthesis produced no final claims.
        </div>
      )}
      {claims.map((c) => {
        const color =
          c.status === "likely_true"
            ? "var(--green)"
            : c.status === "contested"
              ? "var(--amber)"
              : c.status === "likely_false"
                ? "var(--red)"
                : "var(--ink-2)";
        return (
          <div
            key={c.id}
            style={{
              padding: "10px 14px",
              borderBottom: "1px solid var(--line-1)",
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            <div className="row gap-2" style={{ alignItems: "baseline" }}>
              <span className="tt-up" style={{ fontSize: 9, color }}>
                {c.status.replace("_", " ")}
              </span>
              <div style={{ flex: 1 }} />
              <Bar value={c.confidence} width={56} color={color} showVal />
            </div>
            <div style={{ fontSize: 12, color: "var(--ink-0)", lineHeight: 1.5 }}>
              {c.statement}
            </div>
            <div className="muted" style={{ fontSize: 9 }}>
              {c.supporting_evidence.length} support · {c.contradicting_evidence.length} contradict
            </div>
            {c.supporting_evidence.length > 0 && (
              <EvidenceList refs={c.supporting_evidence} label="supporting sources" />
            )}
            {c.contradicting_evidence.length > 0 && (
              <EvidenceList refs={c.contradicting_evidence} label="contradicting sources" />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function DebateRoom() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const transcriptRef = useRef<HTMLDivElement>(null);

  const storedTopic = useDebateStore((s) => s.topic);
  const setStoredTopic = useDebateStore((s) => s.setTopic);

  const urlId = searchParams.get("id");
  const [topic, setTopic] = useState(storedTopic ?? "");
  const [vertical, setVertical] = useState<string>("geopolitics");
  const [discussionId, setDiscussionId] = useState<string | null>(urlId);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);
  const [castSelection, setCastSelection] = useState<CastSelection>(null);

  // Reload an existing discussion when URL id changes (e.g. clicked from /ops).
  useEffect(() => {
    if (urlId && urlId !== discussionId) setDiscussionId(urlId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlId]);

  const stream = useDiscussionStream(discussionId);

  // When loading an existing discussion (URL id), surface its topic in the
  // input so the breadcrumb + RUN copy makes sense.
  useEffect(() => {
    if (urlId && stream.messages.length > 0 && !topic) {
      const first = stream.messages[0];
      // server doesn't return topic on /messages; the breadcrumb pulls it from
      // the discussion detail via stream — leave topic alone, breadcrumb shows id.
      void first;
    }
  }, [urlId, stream.messages, topic]);
  const messageList = stream.messages;
  const sStatus: DStatus = stream.status ?? "planning";
  const hasStatus = stream.status !== null;
  const isTerminal = hasStatus ? TERMINAL.includes(sStatus) : false;
  const failed = stream.status === "failed";
  const messagesCount = messageList.length;
  const finalClaimIds = useMemo(() => stream.claims.map((c) => c.id), [stream.claims]);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [messageList.length]);

  const launch = async () => {
    if (!topic.trim()) return;
    setLaunching(true);
    setLaunchError(null);
    try {
      const res = await api.createDiscussion({ topic: topic.trim(), vertical });
      setDiscussionId(res.discussion_id);
      setStoredTopic(topic.trim());
    } catch (e) {
      setLaunchError(e instanceof Error ? e.message : "failed to start");
    } finally {
      setLaunching(false);
    }
  };

  const breadcrumb = discussionId
    ? `// d-${discussionId.slice(0, 8)} · "${topic}"`
    : `// new deliberation`;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="06·DEBATE"
        title="Debate Room"
        breadcrumb={breadcrumb}
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {discussionId && <ModeIndicator mode={stream.mode} />}
            {hasStatus && <StatusPill s={sStatus} />}
            {hasStatus && (
              <span className="muted tt-up" style={{ fontSize: 9 }}>
                {messagesCount} msg{messagesCount === 1 ? "" : "s"}
              </span>
            )}
            {isTerminal && finalClaimIds.length > 0 && (
              <Btn primary onClick={() => router.push("/library")}>
                VIEW IN LIBRARY →
              </Btn>
            )}
            {discussionId && (
              <Btn
                ghost
                onClick={() => {
                  setDiscussionId(null);
                  setLaunchError(null);
                  setTopic("");
                  setStoredTopic("");
                }}
                title="clear and start a new debate"
              >
                × CLEAR
              </Btn>
            )}
          </div>
        }
      />

      <div
        style={{
          padding: "10px 14px",
          borderBottom: "1px solid var(--line-2)",
          background: "var(--bg-1)",
          display: "flex",
          gap: 10,
          alignItems: "center",
        }}
      >
        <span className="tt-up muted" style={{ fontSize: 9, minWidth: 44 }}>
          TOPIC
        </span>
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !launching) launch();
          }}
          placeholder="ask a question grounded in evidence..."
          className="input"
          style={{ flex: 1, fontSize: 12, padding: "6px 10px" }}
          disabled={launching}
        />
        <span className="tt-up muted" style={{ fontSize: 9 }}>
          VERTICAL
        </span>
        <div style={{ display: "inline-flex", border: "1px solid var(--line-2)" }}>
          {VERTICALS.map((v, i) => {
            const active = v.value === vertical;
            return (
              <button
                type="button"
                key={v.value}
                onClick={() => setVertical(v.value)}
                style={{
                  padding: "5px 9px",
                  fontSize: 10,
                  fontFamily: "inherit",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  background: active ? "var(--amber)" : "transparent",
                  color: active ? "var(--bg-0)" : "var(--ink-1)",
                  border: "none",
                  borderLeft: i === 0 ? "none" : "1px solid var(--line-2)",
                  cursor: "pointer",
                  fontWeight: active ? 600 : 400,
                }}
              >
                {v.label}
              </button>
            );
          })}
        </div>
        <Btn primary onClick={launch} disabled={launching || !topic.trim()}>
          {launching ? "STARTING..." : "▸ RUN"}
        </Btn>
        {launchError && (
          <span style={{ fontSize: 10, color: "var(--red)" }}>{launchError}</span>
        )}
      </div>

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          className="col"
          style={{
            width: 220,
            borderRight: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflow: "hidden",
          }}
        >
          <SectionHeader
            id="P"
            title="Cast"
            sub={`${new Set(messageList.map((m) => m.persona_id ?? m.agent_id)).size} agents · click to view`}
          />
          <CastPanel
            messages={messageList}
            claimCount={stream.claims.length}
            selected={castSelection}
            onSelect={setCastSelection}
          />
        </div>

        <div className="col grow" style={{ overflow: "hidden", background: "var(--bg-0)" }}>
          <CenterView
            transcriptRef={transcriptRef}
            discussionId={discussionId}
            topic={topic}
            messageList={messageList}
            stream={stream}
            sStatus={sStatus}
            hasStatus={hasStatus}
            isTerminal={isTerminal}
            failed={failed}
            castSelection={castSelection}
            onSelect={setCastSelection}
          />
        </div>

        <div
          className="col"
          style={{
            width: 320,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflow: "hidden",
          }}
        >
          <Panel id="S" title="Status" sub={discussionId ? `id ${discussionId.slice(0, 8)}` : "no run"} style={{ flexShrink: 0 }}>
            <div style={{ padding: 14 }}>
              <div className="row gap-2" style={{ alignItems: "baseline" }}>
                <span
                  className="tab"
                  style={{
                    fontSize: 22,
                    color: failed ? "var(--red)" : "var(--amber)",
                    fontWeight: 600,
                  }}
                >
                  {sStatus.toUpperCase()}
                </span>
                <div style={{ flex: 1 }} />
                {hasStatus && <StatusPill s={sStatus} />}
              </div>
              <div className="row" style={{ marginTop: 10, gap: 12, flexWrap: "wrap" }}>
                {(["planning", "researching", "debating", "synthesizing", "completed"] as const).map(
                  (step) => {
                    const active = step === sStatus;
                    const passed =
                      ["planning", "researching", "debating", "synthesizing", "completed"].indexOf(
                        sStatus,
                      ) >=
                      ["planning", "researching", "debating", "synthesizing", "completed"].indexOf(
                        step,
                      );
                    return (
                      <span
                        key={step}
                        className="tt-up"
                        style={{
                          fontSize: 9,
                          color: active
                            ? "var(--amber)"
                            : passed
                              ? "var(--green)"
                              : "var(--ink-3)",
                        }}
                      >
                        {active ? "▸ " : passed ? "· " : "  "}
                        {step}
                      </span>
                    );
                  },
                )}
              </div>
            </div>
          </Panel>

          <Panel
            id="C"
            title="Synthesis"
            sub={hasStatus ? `${finalClaimIds.length} claim${finalClaimIds.length === 1 ? "" : "s"}` : "—"}
            style={{ flex: 1, minHeight: 0 }}
          >
            {sStatus === "completed" ? (
              <SynthesisPanel claims={stream.claims} topic={topic} />
            ) : (
              <div style={{ padding: 14, fontSize: 11, color: "var(--ink-3)" }}>
                synthesis is generated when the debate completes.
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
