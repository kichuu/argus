"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Panel } from "@/components/ui/Panel";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { Sparkline } from "@/components/ui/Sparkline";
import { api, type DiscussionMessage } from "@/lib/api";
import { ARGUS_DATA } from "@/mock/data";
import type { OrchestrationNode } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

const STATE_COLOR: Record<string, string> = {
  idle: "var(--ink-3)",
  thinking: "var(--amber)",
  "tool-call": "var(--cyan)",
  speaking: "var(--green)",
  running: "var(--green)",
};

const W = 1000;
const H = 560;

// Pipeline node order for the derived (live) orchestration view. Persona
// messages all have role "persona" — we group them under one node.
const LIVE_NODE_ORDER = [
  "research",
  "master",
  "personas",
  "critic",
  "synthesizer",
] as const;
type LiveNodeId = (typeof LIVE_NODE_ORDER)[number];

const LIVE_NODE_LABEL: Record<LiveNodeId, string> = {
  research: "RESEARCH",
  master: "MASTER",
  personas: "PERSONAS",
  critic: "CRITIC",
  synthesizer: "SYNTHESIZER",
};

const LIVE_NODE_MODEL: Record<LiveNodeId, string> = {
  research: "haiku-4.5",
  master: "opus-4.1",
  personas: "sonnet-4.5",
  critic: "opus-4.1",
  synthesizer: "opus-4.1",
};

// Map a message role onto a derived-orchestration node id.
function roleToNodeId(role: string | undefined): LiveNodeId | null {
  if (!role) return null;
  const r = role.toLowerCase();
  if (r === "persona" || r === "personas") return "personas";
  if (r === "research" || r === "researcher") return "research";
  if (r === "master" || r === "orchestrator") return "master";
  if (r === "critic") return "critic";
  if (r === "synthesizer" || r === "synthesis" || r === "synth") return "synthesizer";
  return null;
}

// Build a fresh ORCHESTRATION-shaped array from the live message stream.
function buildLiveOrchestration(
  messages: DiscussionMessage[],
  now: number,
): { nodes: OrchestrationNode[]; activeAgeMsByNode: Partial<Record<LiveNodeId, number>> } {
  // x positions roughly mirror the existing column lanes (research / orch /
  // personas / synth) with critic squeezed between personas and synth.
  const X: Record<LiveNodeId, number> = {
    research: 0.24,
    master: 0.42,
    personas: 0.62,
    critic: 0.78,
    synthesizer: 0.92,
  };
  const Y: Record<LiveNodeId, number> = {
    research: 0.5,
    master: 0.5,
    personas: 0.5,
    critic: 0.5,
    synthesizer: 0.5,
  };

  // Most recent message overall — its role flags the "active" node.
  let mostRecent: DiscussionMessage | null = null;
  let mostRecentMs = -Infinity;
  // Most recent timestamp seen *per node*, for the live age readout.
  const lastByNode: Partial<Record<LiveNodeId, number>> = {};
  const seenByNode: Partial<Record<LiveNodeId, boolean>> = {};

  for (const m of messages) {
    const nid = roleToNodeId(m.role);
    if (!nid) continue;
    seenByNode[nid] = true;
    if (m.created_at) {
      const t = Date.parse(m.created_at);
      if (Number.isFinite(t)) {
        if ((lastByNode[nid] ?? -Infinity) < t) lastByNode[nid] = t;
        if (t > mostRecentMs) {
          mostRecentMs = t;
          mostRecent = m;
        }
      }
    }
  }

  const activeNodeId =
    mostRecent && now - mostRecentMs <= 30_000 ? roleToNodeId(mostRecent.role) : null;

  const nodes: OrchestrationNode[] = LIVE_NODE_ORDER.map((id, idx) => {
    const seen = !!seenByNode[id];
    const isActive = activeNodeId === id;
    const state: OrchestrationNode["state"] = isActive
      ? "speaking"
      : seen
        ? "running"
        : "idle";
    const prev = idx > 0 ? LIVE_NODE_ORDER[idx - 1] : null;
    const next = idx < LIVE_NODE_ORDER.length - 1 ? LIVE_NODE_ORDER[idx + 1] : null;
    return {
      id,
      label: LIVE_NODE_LABEL[id],
      x: X[id],
      y: Y[id],
      model: LIVE_NODE_MODEL[id],
      state,
      inEdges: prev ? [prev] : [],
      outEdges: next ? [next] : [],
    };
  });

  const activeAgeMsByNode: Partial<Record<LiveNodeId, number>> = {};
  if (activeNodeId && lastByNode[activeNodeId] != null) {
    activeAgeMsByNode[activeNodeId] = now - (lastByNode[activeNodeId] as number);
  }

  return { nodes, activeAgeMsByNode };
}

export function OpsTheater() {
  const router = useRouter();
  const D = ARGUS_DATA;
  const [tick, setTick] = useState(0);
  const [paused, setPaused] = useState(false);
  const discussionId = useDebateStore((s) => s.discussionId);
  const topic = useDebateStore((s) => s.topic);

  const liveDiscussion = useQuery({
    queryKey: ["discussion", discussionId],
    queryFn: () => api.discussion(discussionId as string),
    enabled: !!discussionId,
    refetchInterval: 2000,
    retry: 0,
    staleTime: 30_000,
  });

  const liveMessages = useQuery({
    queryKey: ["discussion-messages", discussionId],
    queryFn: () => api.discussionMessages(discussionId as string),
    enabled: !!discussionId,
    refetchInterval: 2000,
    retry: 0,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setTick((t) => t + 1), 600);
    return () => clearInterval(id);
  }, [paused]);

  const personaActivity = D.PERSONAS.map((p, i) => {
    const pid = p.id === "indopacom" ? "indo" : p.id;
    const node = D.ORCHESTRATION.find((o) => o.id === `p-${pid}`);
    return {
      p,
      cpu: 30 + ((tick + i * 3) % 70),
      tokens: 1240 + ((tick * 7 + i * 100) % 800),
      state: node?.state ?? "idle",
    };
  });

  const isLive = !!discussionId;
  const apiHealthy = isLive && (liveDiscussion.isSuccess || liveMessages.isSuccess);
  const showMockChip = !isLive || (isLive && (liveDiscussion.isError || liveMessages.isError));
  const liveMsgCount = liveMessages.data?.length ?? 0;
  const liveStatus = liveDiscussion.data?.status;
  const liveTopic = liveDiscussion.data?.topic ?? topic;

  // Derive the orchestration node graph from the live message stream when we
  // have one; otherwise fall back to the mock animation. The fallback covers
  // (a) no discussion launched yet and (b) a launched discussion with zero
  // messages so far.
  const useDerived = isLive && liveMsgCount > 0;
  // `tick` keeps the relative-age readouts ticking even between polls.
  const nowMs = Date.now() + tick * 0;
  const { nodes: derivedNodes, activeAgeMsByNode } = useDerived
    ? buildLiveOrchestration(liveMessages.data ?? [], nowMs)
    : { nodes: [] as OrchestrationNode[], activeAgeMsByNode: {} };
  const orchestrationNodes: OrchestrationNode[] = useDerived
    ? derivedNodes
    : D.ORCHESTRATION;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="04·OPS"
        title="Agent Ops Theater"
        breadcrumb={
          isLive
            ? `// run ${discussionId} · ${(liveTopic || "live").slice(0, 60)}${
                liveStatus ? ` · ${liveStatus}` : ""
              }`
            : "// run d-2026-04-25-01 · Taiwan Strait quarantine · 7 personas"
        }
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {showMockChip && <Chip tone="amber">offline · mock</Chip>}
            {apiHealthy && <Chip tone="green">live · {liveMsgCount} msgs</Chip>}
            <Btn ghost active={!paused} onClick={() => setPaused(false)}>
              ▶ LIVE
            </Btn>
            <Btn ghost active={paused} onClick={() => setPaused(true)}>
              ⏸ PAUSE
            </Btn>
            <Btn ghost>↺ STEP</Btn>
            <Btn ghost>◐ SLOW-MO</Btn>
            <Btn primary onClick={() => router.push("/debate")}>
              OPEN DEBATE ROOM →
            </Btn>
          </div>
        }
      />

      <div className="grow row" style={{ overflow: "hidden" }}>
        <div
          className="grow col"
          style={{ borderRight: "1px solid var(--line-2)", overflow: "hidden" }}
        >
          <div className="grow grid-bg" style={{ position: "relative" }}>
            <svg
              viewBox={`0 0 ${W} ${H}`}
              style={{ width: "100%", height: "100%" }}
              preserveAspectRatio="xMidYMid meet"
            >
              <text x={20} y={48} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">
                INGEST
              </text>
              <text
                x={W * 0.24 - 28}
                y={48}
                fontFamily="JetBrains Mono"
                fontSize="9"
                fill="var(--ink-3)"
              >
                RESEARCH
              </text>
              <text
                x={W * 0.45 - 50}
                y={48}
                fontFamily="JetBrains Mono"
                fontSize="9"
                fill="var(--ink-3)"
              >
                ORCHESTRATION
              </text>
              <text
                x={W * 0.66 - 38}
                y={48}
                fontFamily="JetBrains Mono"
                fontSize="9"
                fill="var(--ink-3)"
              >
                PERSONAS · 7
              </text>
              <text
                x={W * 0.88 - 38}
                y={48}
                fontFamily="JetBrains Mono"
                fontSize="9"
                fill="var(--ink-3)"
              >
                SYNTHESIZER
              </text>

              {[0.16, 0.34, 0.55, 0.78].map((x) => (
                <line
                  key={x}
                  x1={x * W}
                  y1={20}
                  x2={x * W}
                  y2={H - 20}
                  stroke="var(--line-1)"
                  strokeDasharray="3 5"
                />
              ))}

              {orchestrationNodes.flatMap((node) =>
                node.outEdges.map((toId) => {
                  const to = orchestrationNodes.find((n) => n.id === toId);
                  if (!to) return null;
                  const x1 = node.x * W;
                  const y1 = node.y * H;
                  const x2 = to.x * W;
                  const y2 = to.y * H;
                  const active = node.state !== "idle" && to.state !== "idle";
                  return (
                    <g key={`${node.id}-${toId}`}>
                      <line
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        stroke={active ? "var(--amber)" : "var(--line-2)"}
                        strokeWidth={active ? 1 : 0.5}
                        strokeDasharray={active ? "4 4" : "0"}
                        opacity={active ? 0.8 : 0.5}
                      >
                        {active && (
                          <animate
                            attributeName="stroke-dashoffset"
                            from="0"
                            to="-16"
                            dur="0.6s"
                            repeatCount="indefinite"
                          />
                        )}
                      </line>
                    </g>
                  );
                }),
              )}

              {D.ORCHESTRATION.map((n) => {
                const x = n.x * W;
                const y = n.y * H;
                const c = STATE_COLOR[n.state];
                const isPersona = n.id.startsWith("p-");
                const w = isPersona ? 92 : 110;
                const h = 32;
                return (
                  <g key={n.id} style={{ cursor: "pointer" }}>
                    <rect
                      x={x - w / 2}
                      y={y - h / 2}
                      width={w}
                      height={h}
                      fill="var(--bg-2)"
                      stroke={c}
                      strokeWidth="1"
                    />
                    <text
                      x={x}
                      y={y - 2}
                      fontFamily="JetBrains Mono"
                      fontSize="10"
                      fill="var(--ink-0)"
                      textAnchor="middle"
                      fontWeight="600"
                    >
                      {n.label}
                    </text>
                    <text
                      x={x}
                      y={y + 9}
                      fontFamily="JetBrains Mono"
                      fontSize="8"
                      fill={c}
                      textAnchor="middle"
                    >
                      {n.state === "thinking"
                        ? "◐ thinking"
                        : n.state === "tool-call"
                          ? "▸ tool"
                          : n.state === "speaking"
                            ? "◉ speak"
                            : "○ idle"}
                    </text>
                    {n.state !== "idle" && (
                      <circle cx={x + w / 2 - 6} cy={y - h / 2 + 6} r="2.5" fill={c}>
                        <animate
                          attributeName="opacity"
                          from="1"
                          to="0.3"
                          dur="1s"
                          repeatCount="indefinite"
                        />
                      </circle>
                    )}
                  </g>
                );
              })}
            </svg>

            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                background: "var(--bg-2)",
                borderTop: "1px solid var(--line-2)",
                height: 78,
                overflow: "hidden",
                padding: "6px 12px",
              }}
            >
              <div
                className="tt-up"
                style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 4 }}
              >
                SYSTEM EVENT TAPE · realtime
              </div>
              <div
                style={{
                  fontSize: 10,
                  lineHeight: 1.5,
                  color: "var(--ink-1)",
                  fontFamily: "JetBrains Mono",
                }}
              >
                <div>
                  <span className="tab muted">14:22:08.412</span>{" "}
                  <span className="green">orchestrator</span> &gt; cast 7 personas; depth=deep;
                  turn-limit=14
                </div>
                <div>
                  <span className="tab muted">14:22:08.821</span>{" "}
                  <span className="amber">p-indopacom</span> &gt; tool_call(kg.path(&quot;us&quot;,&quot;tw&quot;)) → 4 paths
                </div>
                <div>
                  <span className="tab muted">14:22:09.114</span>{" "}
                  <span className="cyan">p-analyst</span> &gt; memory_write key=&quot;quarantine.prob&quot; val=0.42
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col" style={{ width: 360, overflow: "hidden" }}>
          <Panel id="R1" title="Resource Meter" sub="last 60s" style={{ flexShrink: 0 }}>
            <div
              style={{
                padding: 14,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 14,
              }}
            >
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  TOK / MIN
                </div>
                <div
                  className="tab"
                  style={{ fontSize: 22, color: "var(--amber)", fontWeight: 600 }}
                >
                  14,281
                </div>
                <Sparkline
                  data={[8, 12, 9, 14, 18, 16, 22, 19, 25, 21, 24, 28, 26, 24, 22, 28, 31, 28]}
                  width={140}
                  height={24}
                />
              </div>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  COST / RUN
                </div>
                <div
                  className="tab"
                  style={{ fontSize: 22, color: "var(--ink-0)", fontWeight: 600 }}
                >
                  $0.31
                </div>
                <Sparkline
                  data={[2, 3, 2, 4, 5, 4, 6, 5, 7, 6, 7, 8, 7, 7, 6, 8, 9, 8]}
                  width={140}
                  height={24}
                  color="var(--green)"
                />
              </div>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  QUEUE
                </div>
                <div className="tab" style={{ fontSize: 14, color: "var(--ink-0)" }}>
                  3 / 16
                </div>
              </div>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  ERRORS 1H
                </div>
                <div className="tab" style={{ fontSize: 14, color: "var(--green)" }}>
                  0
                </div>
              </div>
            </div>
            <div style={{ padding: "0 14px 14px" }}>
              <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 4 }}>
                MODEL MIX
              </div>
              <div style={{ display: "flex", height: 8, border: "1px solid var(--line-2)" }}>
                <div style={{ width: "42%", background: "var(--p-3)" }} title="Sonnet" />
                <div style={{ width: "31%", background: "var(--amber)" }} title="Opus" />
                <div style={{ width: "27%", background: "var(--p-2)" }} title="Haiku" />
              </div>
              <div
                className="row"
                style={{
                  fontSize: 9,
                  marginTop: 4,
                  color: "var(--ink-2)",
                  justifyContent: "space-between",
                }}
              >
                <span>SONNET 42%</span>
                <span>OPUS 31%</span>
                <span>HAIKU 27%</span>
              </div>
            </div>
          </Panel>

          <Panel
            id="R3"
            title="Live Messages"
            sub={isLive ? `stream · ${liveMsgCount} turns` : "no live discussion"}
            style={{ flexShrink: 0, maxHeight: 220 }}
          >
            <div className="col" style={{ overflowY: "auto", maxHeight: 200 }}>
              {!discussionId ? (
                <EmptyState
                  title="No live discussion"
                  hint="Launch from Home to see agent messages"
                  cta={{ label: "GO HOME", onClick: () => router.push("/") }}
                  style={{ margin: 12 }}
                />
              ) : liveMessages.isLoading ? (
                <Skeleton rows={4} rowHeight={12} />
              ) : liveMessages.isError ? (
                <ErrorBox
                  message="failed to load live messages"
                  onRetry={() => liveMessages.refetch()}
                  style={{ margin: 12 }}
                />
              ) : (liveMessages.data?.length ?? 0) === 0 ? (
                <EmptyState
                  title="Waiting for first turn"
                  hint="Personas are warming up"
                  style={{ margin: 12 }}
                />
              ) : (
                (liveMessages.data ?? []).slice(-12).map((m, i) => (
                  <div
                    key={(m.id as string | undefined) ?? i}
                    style={{
                      padding: "8px 12px",
                      borderBottom: "1px solid var(--line-1)",
                      fontSize: 10,
                      lineHeight: 1.4,
                    }}
                  >
                    <div className="row gap-2" style={{ alignItems: "baseline" }}>
                      <span className="amber tt-up" style={{ fontSize: 9 }}>
                        {m.persona_id ?? m.agent_id ?? m.role ?? "agent"}
                      </span>
                      <span className="tab muted" style={{ fontSize: 9 }}>
                        {m.created_at?.slice(11, 19) ?? ""}
                      </span>
                    </div>
                    <div style={{ color: "var(--ink-1)", marginTop: 2 }}>
                      {(m.content ?? "").slice(0, 180)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Panel>

          <Panel id="R2" title="Persona Activity" sub="live · thought / tool / speak" style={{ flex: 1 }}>
            <div className="col" style={{ overflowY: "auto" }}>
              {personaActivity.map(({ p, cpu, tokens, state }) => (
                <div
                  key={p.id}
                  style={{
                    padding: "10px 12px",
                    borderBottom: "1px solid var(--line-1)",
                  }}
                >
                  <div className="row gap-2" style={{ alignItems: "center" }}>
                    <PersonaAvatar p={p} size={20} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, color: "var(--ink-0)" }}>{p.name}</div>
                      <div style={{ fontSize: 9, color: "var(--ink-2)" }}>{p.model}</div>
                    </div>
                    <span
                      className="tt-up"
                      style={{ fontSize: 9, color: STATE_COLOR[state] }}
                    >
                      {state === "idle"
                        ? "○ idle"
                        : state === "thinking"
                          ? "◐ think"
                          : state === "tool-call"
                            ? "▸ tool"
                            : "◉ speak"}
                    </span>
                  </div>
                  <div className="row gap-2" style={{ marginTop: 6, alignItems: "center" }}>
                    <Bar value={cpu} max={100} width={140} color={p.colorVar} />
                    <span className="tab muted" style={{ fontSize: 9 }}>
                      {tokens} tok
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
