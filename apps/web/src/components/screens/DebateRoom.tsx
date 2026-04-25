"use client";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { AsciiSpinner } from "@/components/ui/AsciiSpinner";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { useDiscussionStream, type StreamMode } from "@/hooks/useDiscussionStream";
import {
  api,
  type AgentMessage,
  type Claim,
  type DiscussionStatus as DStatus,
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
        </div>
      </div>
    </div>
  );
}

function CastPanel({ messages }: { messages: AgentMessage[] }) {
  const groups = useMemo(() => {
    const map = new Map<string, { key: string; agent: string; count: number; last: string }>();
    for (const m of messages) {
      const key = m.persona_id ?? m.agent_id ?? m.role;
      const existing = map.get(key);
      if (existing) {
        existing.count += 1;
        existing.last = m.created_at;
      } else {
        map.set(key, { key, agent: m.agent_id, count: 1, last: m.created_at });
      }
    }
    return Array.from(map.values());
  }, [messages]);

  return (
    <div className="col" style={{ overflowY: "auto" }}>
      {groups.length === 0 ? (
        <div style={{ padding: "12px 14px", fontSize: 11, color: "var(--ink-3)" }}>
          ── awaiting cast ──
        </div>
      ) : (
        groups.map((g) => {
          const color = colorFor(g.key);
          return (
            <div
              key={g.key}
              style={{
                padding: "10px 12px",
                borderBottom: "1px solid var(--line-1)",
                display: "flex",
                gap: 8,
                alignItems: "center",
                borderLeft: `2px solid ${color}`,
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
                    color: "var(--ink-0)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {g.agent}
                </div>
                <div style={{ fontSize: 9, color: "var(--ink-2)" }}>
                  {g.count} msg{g.count === 1 ? "" : "s"} · {relTime(g.last)}
                </div>
              </div>
            </div>
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

function SynthesisPanel({ claims }: { claims: Claim[] }) {
  return (
    <div className="col" style={{ overflowY: "auto" }}>
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
          </div>
        );
      })}
    </div>
  );
}

export function DebateRoom() {
  const router = useRouter();
  const transcriptRef = useRef<HTMLDivElement>(null);

  const storedTopic = useDebateStore((s) => s.topic);
  const setStoredTopic = useDebateStore((s) => s.setTopic);

  const [topic, setTopic] = useState(storedTopic ?? "");
  const [vertical, setVertical] = useState<string>("geopolitics");
  const [discussionId, setDiscussionId] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  const stream = useDiscussionStream(discussionId);
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
          <SectionHeader id="P" title="Cast" sub={`${new Set(messageList.map((m) => m.persona_id ?? m.agent_id)).size} agents`} />
          <CastPanel messages={messageList} />
        </div>

        <div className="col grow" style={{ overflow: "hidden", background: "var(--bg-0)" }}>
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
            {messageList.map((m) => (
              <MessageRow key={m.id} m={m} />
            ))}
            {discussionId && hasStatus && !isTerminal && (
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
            {sStatus === "completed" && (
              <div
                style={{
                  padding: 24,
                  textAlign: "center",
                  color: "var(--ink-2)",
                  fontSize: 11,
                }}
              >
                ─── debate concluded · synthesis below ───
              </div>
            )}
          </div>
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
              <SynthesisPanel claims={stream.claims} />
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
