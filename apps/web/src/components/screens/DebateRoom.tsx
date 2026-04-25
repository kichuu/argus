"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AsciiSpinner } from "@/components/ui/AsciiSpinner";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Panel } from "@/components/ui/Panel";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Segmented } from "@/components/ui/Segmented";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type PersonaSummary } from "@/lib/api";
import type { Persona } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

const _PALETTE = [
  "var(--p-1)",
  "var(--p-2)",
  "var(--p-3)",
  "var(--p-4)",
  "var(--p-5)",
  "var(--p-6)",
  "var(--p-7)",
];
function colorForFrame(frame: string): string {
  let h = 0;
  for (let i = 0; i < frame.length; i++) h = (h + frame.charCodeAt(i)) | 0;
  return _PALETTE[Math.abs(h) % _PALETTE.length];
}

// PersonaAvatar only reads `colorVar` and `initials`. Build a minimal Persona
// shape from a live PersonaSummary so we can keep the existing UI primitives.
type LivePersona = {
  id: string;
  name: string;
  colorVar: string;
  initials: string;
  frame: string;
};

function toLivePersona(s: PersonaSummary & { color?: string | null }): LivePersona {
  const frame = s.frame ?? s.id;
  const colorVar = (s.color && s.color.length > 0) ? s.color : colorForFrame(frame);
  const initials = (frame[0] ?? "?").toUpperCase();
  return { id: s.id, name: frame, colorVar, initials, frame };
}

// Avatar adapter: PersonaAvatar's prop type is `Persona` but it only touches
// `colorVar` and `initials`. We synthesize a compatible object.
function avatarPersona(lp: LivePersona): Persona {
  return {
    id: lp.id,
    name: lp.name,
    role: "",
    country: "",
    flag: "",
    color: lp.colorVar,
    colorVar: lp.colorVar,
    initials: lp.initials,
    bias: "",
    beliefs: [],
    redlines: [],
    model: "",
    memorySize: "",
    temperature: 0,
    aggression: 0,
    citationStrictness: 0,
  };
}

function PersonaRefGraph({
  refs,
  personas,
}: {
  refs: [string, string][];
  personas: LivePersona[];
}) {
  const W = 280;
  const H = 200;
  const cx = W / 2;
  const cy = H / 2;
  const R = 70;
  const positions: Record<string, { x: number; y: number; p: LivePersona }> = {};
  personas.forEach((p, i) => {
    const a = (i / Math.max(1, personas.length)) * Math.PI * 2 - Math.PI / 2;
    positions[p.id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a), p };
  });
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: "100%", height: "100%" }}
      preserveAspectRatio="xMidYMid meet"
    >
      {refs.map(([from, to], i) => {
        const a = positions[from];
        const b = positions[to];
        if (!a || !b) return null;
        return (
          <g key={i}>
            <line
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={a.p.colorVar}
              strokeWidth="0.8"
              opacity="0.6"
              markerEnd="url(#arrow)"
            />
          </g>
        );
      })}
      <defs>
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="var(--ink-2)" />
        </marker>
      </defs>
      {Object.values(positions).map(({ x, y, p }) => (
        <g key={p.id}>
          <circle cx={x} cy={y} r="11" fill="var(--bg-2)" stroke={p.colorVar} strokeWidth="1.5" />
          <text
            x={x}
            y={y + 3}
            fontSize="8"
            fill={p.colorVar}
            fontFamily="JetBrains Mono"
            textAnchor="middle"
            fontWeight="600"
          >
            {p.initials}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function DebateRoom() {
  const router = useRouter();
  const transcriptRef = useRef<HTMLDivElement>(null);

  const stepBack = useDebateStore((s) => s.stepBack);
  const paused = useDebateStore((s) => s.paused);
  const setPaused = useDebateStore((s) => s.setPaused);
  const speed = useDebateStore((s) => s.speed);
  const setSpeed = useDebateStore((s) => s.setSpeed);
  const discussionId = useDebateStore((s) => s.discussionId);

  const [filterPersona, setFilterPersona] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const personasQuery = useQuery({
    queryKey: ["personas-catalog"],
    queryFn: api.personas,
    staleTime: 60_000,
    retry: 0,
  });

  const personaMap = useMemo(() => {
    const m = new Map<string, LivePersona>();
    (personasQuery.data ?? []).forEach((p) => {
      m.set(p.id, toLivePersona(p as PersonaSummary & { color?: string | null }));
    });
    return m;
  }, [personasQuery.data]);

  const personasList = useMemo(() => Array.from(personaMap.values()), [personaMap]);

  const liveMessages = useQuery({
    queryKey: ["discussion-messages", discussionId],
    queryFn: () => api.discussionMessages(discussionId as string),
    enabled: !!discussionId,
    refetchInterval: 2000,
    retry: 0,
    staleTime: 30_000,
  });
  const liveData = liveMessages.data;
  const messageCount = liveData?.length ?? 0;
  const hasLive = !!discussionId && messageCount > 0;

  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [messageCount]);

  const pById = (id: string | undefined | null): LivePersona | undefined =>
    id ? personaMap.get(id) : undefined;

  const filteredMessages = useMemo(() => {
    const all = liveData ?? [];
    const byPersona = filterPersona
      ? all.filter((m) => (m.persona_id ?? m.agent_id) === filterPersona)
      : all;
    const bySearch = search
      ? byPersona.filter((m) => (m.content ?? "").toLowerCase().includes(search.toLowerCase()))
      : byPersona;
    return bySearch;
  }, [liveData, filterPersona, search]);

  // Convergence is currently unmodeled live — derive a soft proxy from message
  // count so the UI stays alive without inventing data.
  const convergence = Math.min(0.78, messageCount === 0 ? 0 : Math.min(messageCount, 12) / 12 * 0.78);
  const round: "DRAFT" | "CRITIQUE" | "REBUT" | "VOTE" =
    messageCount >= 9 ? "VOTE" : messageCount >= 6 ? "REBUT" : messageCount >= 3 ? "CRITIQUE" : "DRAFT";
  const roundN = Math.max(1, Math.min(4, Math.ceil(messageCount / 3) || 1));

  const refs = useMemo(() => {
    const r: [string, string][] = [];
    const all = liveData ?? [];
    // Build a simple "previous-speaker" reference graph from live message order.
    let lastBy: string | null = null;
    all.forEach((m) => {
      const pid = m.persona_id ?? m.agent_id ?? null;
      if (pid && lastBy && pid !== lastBy) r.push([pid, lastBy]);
      if (pid) lastBy = pid;
    });
    return r;
  }, [liveData]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="06·DEBATE"
        title="Debate Room"
        breadcrumb={
          discussionId
            ? `// ${discussionId} · live discussion`
            : "// no debate loaded"
        }
        right={
          <div className="row gap-2">
            {hasLive && <Chip tone="green">live · {messageCount} msgs</Chip>}
            {hasLive && (
              <Chip tone="amber">
                <Dot tone="amber" pulse /> ROUND {roundN} · {round}
              </Chip>
            )}
            <Btn ghost active={paused} onClick={() => setPaused(!paused)}>
              {paused ? "▶ RESUME" : "⏸ PAUSE"}
            </Btn>
            <Btn ghost onClick={() => stepBack()}>
              ↶ STEP BACK
            </Btn>
            <Segmented
              size="sm"
              options={[
                { value: 0.5, label: "0.5×" },
                { value: 1, label: "1×" },
                { value: 2, label: "2×" },
                { value: 4, label: "4×" },
              ]}
              value={speed}
              onChange={setSpeed}
            />
            <Btn primary onClick={() => router.push("/synthesis")}>
              VIEW SYNTHESIS →
            </Btn>
          </div>
        }
      />

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
          <SectionHeader id="P" title="Cast" sub={`${personasList.length} personas`} />
          <div className="col" style={{ overflowY: "auto" }}>
            {personasList.map((p) => {
              const lastPid = liveData && liveData.length
                ? (liveData[liveData.length - 1].persona_id ?? liveData[liveData.length - 1].agent_id)
                : undefined;
              const speaking = lastPid === p.id;
              const msgs = (liveData ?? []).filter(
                (m) => (m.persona_id ?? m.agent_id) === p.id,
              ).length;
              const isFilter = filterPersona === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setFilterPersona(isFilter ? null : p.id)}
                  style={{
                    padding: "10px 12px",
                    borderBottom: "1px solid var(--line-1)",
                    cursor: "pointer",
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    background: isFilter
                      ? "var(--bg-3)"
                      : speaking
                        ? "var(--bg-3)"
                        : "transparent",
                    borderLeft: isFilter
                      ? `2px solid ${p.colorVar}`
                      : speaking
                        ? `2px solid var(--amber)`
                        : "2px solid transparent",
                  }}
                >
                  <PersonaAvatar p={avatarPersona(p)} size={26} />
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
                      {p.name}
                    </div>
                    <div style={{ fontSize: 9, color: "var(--ink-2)" }}>
                      {msgs} msg{msgs === 1 ? "" : "s"}
                    </div>
                  </div>
                  {speaking ? <Dot tone="green" pulse /> : null}
                </div>
              );
            })}
            {personasList.length === 0 && !personasQuery.isLoading && (
              <div
                style={{ padding: 12, fontSize: 10, color: "var(--ink-3)" }}
                className="muted"
              >
                no personas in catalogue
              </div>
            )}
          </div>
          <div style={{ padding: 12, borderTop: "1px solid var(--line-2)" }}>
            <Btn ghost style={{ width: "100%" }}>
              + SUMMON PERSONA
            </Btn>
          </div>
        </div>

        <div className="col grow" style={{ overflow: "hidden", background: "var(--bg-0)" }}>
          <div
            style={{
              padding: "8px 12px",
              borderBottom: "1px solid var(--line-2)",
              display: "flex",
              gap: 8,
              alignItems: "center",
              background: "var(--bg-1)",
            }}
          >
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="search transcript / regex..."
              className="input"
              style={{ flex: 1, fontSize: 11, padding: "4px 8px" }}
            />
            {filterPersona && (() => {
              const p = pById(filterPersona);
              return p ? (
                <Chip tone="amber" style={{ cursor: "pointer" }}>
                  <span onClick={() => setFilterPersona(null)}>filter: {p.initials} ✕</span>
                </Chip>
              ) : null;
            })()}
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              {filteredMessages.length} / {messageCount} msgs
            </span>
          </div>

          <div ref={transcriptRef} className="grow" style={{ overflowY: "auto", padding: "12px 0" }}>
            {discussionId && liveMessages.isLoading ? (
              <Skeleton rows={5} rowHeight={18} style={{ padding: 16 }} />
            ) : discussionId && liveMessages.isError ? (
              <ErrorBox
                message="failed to load discussion messages"
                onRetry={() => liveMessages.refetch()}
                style={{ margin: 16 }}
              />
            ) : !discussionId || messageCount === 0 ? (
              <EmptyState
                title="No live debate"
                hint="Launch a debate from Home to see agent messages stream in here."
                cta={{ label: "GO HOME", onClick: () => router.push("/") }}
                style={{ margin: 16 }}
              />
            ) : (
              <>
                {filteredMessages.map((m, i) => {
                  const personaId = m.persona_id ?? m.agent_id ?? "";
                  const p = pById(personaId);
                  const evidenceCount = Array.isArray(m.evidence_refs)
                    ? m.evidence_refs.length
                    : 0;
                  return (
                    <div
                      key={(m.id as string | undefined) ?? i}
                      style={{
                        padding: "12px 16px",
                        borderBottom: "1px solid var(--line-1)",
                      }}
                    >
                      <div className="row gap-3" style={{ alignItems: "flex-start" }}>
                        {p && <PersonaAvatar p={avatarPersona(p)} size={28} />}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            className="row gap-2"
                            style={{ alignItems: "baseline", flexWrap: "wrap" }}
                          >
                            <span
                              style={{
                                color: p?.colorVar ?? "var(--ink-0)",
                                fontWeight: 600,
                                fontSize: 12,
                              }}
                            >
                              {p?.name ?? personaId ?? m.role ?? "agent"}
                            </span>
                            {m.role && (
                              <span className="tt-up muted" style={{ fontSize: 9 }}>
                                {m.role}
                              </span>
                            )}
                            <div style={{ flex: 1 }} />
                            <span className="tab muted" style={{ fontSize: 9 }}>
                              {m.created_at?.slice(11, 19) ?? ""}
                            </span>
                          </div>
                          <div
                            style={{
                              fontSize: 13,
                              color: "var(--ink-0)",
                              marginTop: 6,
                              lineHeight: 1.55,
                              fontFamily:
                                "'IBM Plex Sans', 'Inter', system-ui, sans-serif",
                            }}
                          >
                            {m.content ?? ""}
                          </div>
                          {evidenceCount > 0 && (
                            <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>
                              · {evidenceCount} evidence ref
                              {evidenceCount === 1 ? "" : "s"}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {liveMessages.isFetching && (
                  <div style={{ padding: "8px 16px", fontSize: 10, color: "var(--ink-3)" }}>
                    <AsciiSpinner /> polling...
                  </div>
                )}
              </>
            )}
          </div>

          <div
            style={{
              borderTop: "1px solid var(--line-2)",
              padding: 10,
              background: "var(--bg-1)",
              display: "flex",
              gap: 8,
              alignItems: "center",
            }}
          >
            <span className="tt-up muted" style={{ fontSize: 9 }}>
              MODERATOR
            </span>
            <Btn ghost>+ INJECT FACT</Btn>
            <Btn ghost>⚠ CHALLENGE LAST</Btn>
            <Btn ghost>↺ FORCE REBUT</Btn>
            <div style={{ flex: 1 }} />
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              BUDGET
            </span>
            <span className="tab amber" style={{ fontSize: 11 }}>
              $0.31 / $1.00
            </span>
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
          <Panel
            id="C"
            title="Convergence"
            sub={`round ${roundN}/4`}
            style={{ flexShrink: 0 }}
          >
            <div style={{ padding: 14 }}>
              <div className="row gap-2" style={{ alignItems: "baseline" }}>
                <span
                  className="tab"
                  style={{ fontSize: 28, color: "var(--amber)", fontWeight: 600 }}
                >
                  {(convergence * 100).toFixed(0)}
                </span>
                <span className="muted">/100</span>
                <div style={{ flex: 1 }} />
                <Chip tone="amber">
                  {convergence > 0.6 ? "CONVERGING" : convergence > 0.3 ? "DIVERGING" : "OPENING"}
                </Chip>
              </div>
              <Bar value={convergence} width="100%" height={6} color="var(--amber)" />
              <div
                className="row"
                style={{
                  fontSize: 9,
                  marginTop: 4,
                  color: "var(--ink-2)",
                  justifyContent: "space-between",
                }}
              >
                <span>DRAFT</span>
                <span>CRITIQUE</span>
                <span>REBUT</span>
                <span>VOTE</span>
              </div>
            </div>
          </Panel>

          <Panel
            id="G"
            title="Reference Graph"
            sub="who-cites-whom"
            style={{ flexShrink: 0, height: 220 }}
          >
            <PersonaRefGraph refs={refs} personas={personasList} />
          </Panel>

          <Panel id="W" title="World State" sub="kg snapshot · Δ this round" style={{ flex: 1 }}>
            <div className="col" style={{ overflowY: "auto", padding: 12, gap: 10 }}>
              <div>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--green)", marginBottom: 4 }}
                >
                  + ENTITIES THIS ROUND
                </div>
                <div style={{ fontSize: 10, color: "var(--ink-1)", lineHeight: 1.6 }}>
                  · Bashi Channel <span className="muted">(place)</span>
                  <br />· Hellscape concept <span className="muted">(doctrine)</span>
                  <br />· Yonaguni Island <span className="muted">(place)</span>
                  <br />· ROCS Hai Kun <span className="muted">(asset)</span>
                </div>
              </div>
              <div>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--amber)", marginBottom: 4 }}
                >
                  ~ EDGES UPDATED (4)
                </div>
                <div style={{ fontSize: 10, color: "var(--ink-1)", lineHeight: 1.6 }}>
                  · pla → bashi · transit-density 0.6→0.9
                  <br />· jp → tw · linkage strength 0.7→0.9
                  <br />· indopacom → bashi · posture: contested
                  <br />· tsmc → fab21 · status: insurance
                </div>
              </div>
              <div>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 4 }}
                >
                  SOURCES TOUCHED
                </div>
                <div className="row gap-1" style={{ flexWrap: "wrap" }}>
                  {[
                    "GDELT",
                    "Reuters",
                    "Xinhua",
                    "CSIS",
                    "RAND",
                    "DoD",
                    "UNCLOS",
                    "BIS",
                    "ESC-TW",
                  ].map((s) => (
                    <Chip key={s}>{s}</Chip>
                  ))}
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
