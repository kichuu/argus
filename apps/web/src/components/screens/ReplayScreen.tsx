"use client";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { MockBadge } from "@/components/ui/MockBadge";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type DiscussionMessage, type DiscussionSummary } from "@/lib/api";
import { ARGUS_DATA, type Persona } from "@/mock/data";

// NOTE: branches are demo-only — there is no persistence layer for them yet,
// so the SVG branch tree and the right-hand "branch · inject TSMC fire" panel
// remain mock data even when the main timeline is live.
const BRANCHES = [
  { id: "main", label: "main", color: "var(--amber)", events: [0, 2, 4, 6, 8, 10, 12], current: true },
  { id: "b1", label: "branch · inject TSMC fire", color: "var(--p-2)", events: [4, 6, 8] },
  { id: "b2", label: "branch · swap Lai → Hou Yu-ih", color: "var(--p-4)", events: [2, 4, 6, 8] },
  { id: "b3", label: "branch · add EU persona", color: "var(--p-3)", events: [6, 8, 10, 11] },
];

type LooseDiscussion = DiscussionSummary;

function pickMostRecentCompleted(discussions: LooseDiscussion[]): LooseDiscussion | null {
  if (!discussions.length) return null;
  const completed = discussions
    .filter((d) => d.status === "completed")
    .sort((a, b) => {
      const at = new Date(a.completed_at ?? a.started_at ?? a.created_at ?? 0).getTime();
      const bt = new Date(b.completed_at ?? b.started_at ?? b.created_at ?? 0).getTime();
      return bt - at;
    });
  return completed[0] ?? null;
}

// Best-effort persona lookup. Live messages don't yet carry a persona_id
// matching the mock catalogue, so we fall back through the cast list.
function lookupPersona(m: DiscussionMessage, fallbackIdx: number): Persona | null {
  const id = m.persona_id ?? m.agent_id;
  if (id) {
    const hit = ARGUS_DATA.PERSONAS.find((p) => p.id === id);
    if (hit) return hit;
  }
  return ARGUS_DATA.PERSONAS[fallbackIdx % ARGUS_DATA.PERSONAS.length] ?? null;
}

export function ReplayScreen() {
  const discussionsQuery = useQuery({
    queryKey: ["recent-discussions"],
    queryFn: api.discussions,
    staleTime: 60_000,
    retry: 0,
  });

  const recent = useMemo(
    () => pickMostRecentCompleted((discussionsQuery.data ?? []) as LooseDiscussion[]),
    [discussionsQuery.data],
  );

  const messagesQuery = useQuery({
    queryKey: ["replay-messages", recent?.id],
    queryFn: () => api.discussionMessages(recent!.id),
    enabled: !!recent?.id,
    staleTime: 60_000,
    retry: 0,
  });

  const liveMessages = (messagesQuery.data ?? []) as DiscussionMessage[];
  const isLoading = discussionsQuery.isLoading || (recent && messagesQuery.isLoading);
  const apiOnline = !!recent && liveMessages.length > 0;
  const totalLen = apiOnline ? liveMessages.length : ARGUS_DATA.TRANSCRIPT.length;

  const [scrub, setScrub] = useState(8);

  // Clamp scrub once we know the real range.
  const clampedScrub = Math.min(Math.max(scrub, 0), Math.max(totalLen, 0));

  if (isLoading) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader code="09·REPLAY" title="Replay & Branch" breadcrumb="// loading…" />
        <Skeleton rows={10} rowHeight={20} style={{ padding: 24 }} />
      </div>
    );
  }

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="09·REPLAY"
        title="Replay & Branch"
        breadcrumb={
          apiOnline
            ? `// ${recent?.id ?? "—"} · scrubbing turn ${clampedScrub}/${totalLen} · ${BRANCHES.length} branches (mock)`
            : `// d-2026-04-25-01 · scrubbing turn ${clampedScrub}/${totalLen} · ${BRANCHES.length} branches`
        }
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            <MockBadge online={apiOnline} loading={false} />
            <Btn ghost>+ INJECT FACT</Btn>
            <Btn ghost>↻ SWAP PERSONA</Btn>
            <Btn ghost>⊕ NEW BRANCH</Btn>
            <Btn primary>SAVE BRANCH</Btn>
          </div>
        }
      />

      <div className="grow row" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div style={{ padding: 16, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="row gap-2"
              style={{ alignItems: "center", marginBottom: 8, justifyContent: "space-between" }}
            >
              <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
                BRANCH TREE
              </span>
              <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                branches · demo-only (no persistence yet)
              </span>
            </div>
            <svg viewBox="0 0 1000 180" style={{ width: "100%", height: 180 }}>
              {BRANCHES.map((b, bi) => {
                const y = 24 + bi * 40;
                return (
                  <g key={b.id}>
                    <line x1={40} y1={y} x2={960} y2={y} stroke="var(--line-1)" strokeDasharray="2 4" />
                    <text x={20} y={y + 3} fontSize="9" fill={b.color} fontFamily="JetBrains Mono">
                      {b.label}
                    </text>
                    {b.events.map((eIdx, i) => {
                      const x = 60 + eIdx * 70;
                      const isScrub = b.current && eIdx === clampedScrub - 1;
                      return (
                        <g key={i}>
                          <circle
                            cx={x}
                            cy={y}
                            r={isScrub ? 7 : 4}
                            fill={b.color}
                            stroke="var(--bg-1)"
                            strokeWidth="2"
                          />
                          {isScrub && (
                            <circle
                              cx={x}
                              cy={y}
                              r={11}
                              fill="none"
                              stroke={b.color}
                              strokeWidth="1"
                              opacity="0.5"
                            />
                          )}
                        </g>
                      );
                    })}
                    {bi > 0 && b.events.length > 0 && (
                      <line
                        x1={60 + b.events[0] * 70}
                        y1={24}
                        x2={60 + b.events[0] * 70}
                        y2={y - 5}
                        stroke={b.color}
                        strokeWidth="1"
                      />
                    )}
                  </g>
                );
              })}
              <text
                x={500}
                y={172}
                fontSize="9"
                fill="var(--ink-3)"
                fontFamily="JetBrains Mono"
                textAnchor="middle"
              >
                turn 0 ─── {totalLen} (synth)
              </text>
            </svg>
          </div>

          <div className="grow row" style={{ overflow: "hidden" }}>
            <div className="grow col" style={{ borderRight: "1px solid var(--line-2)" }}>
              <SectionHeader
                id="ORIG"
                title={apiOnline ? `main · ${recent?.id ?? ""}` : "main"}
                sub={`turn ${clampedScrub}`}
              />
              <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
                {apiOnline
                  ? liveMessages
                      .slice(Math.max(0, clampedScrub - 2), clampedScrub)
                      .map((m, i) => {
                        const absoluteIdx = Math.max(0, clampedScrub - 2) + i;
                        const p = lookupPersona(m, absoluteIdx);
                        if (!p) return null;
                        return (
                          <div
                            key={m.id ?? absoluteIdx}
                            style={{
                              marginBottom: 14,
                              paddingBottom: 14,
                              borderBottom: "1px solid var(--line-1)",
                            }}
                          >
                            <div
                              className="row gap-2"
                              style={{ alignItems: "center", marginBottom: 4 }}
                            >
                              <PersonaAvatar p={p} size={20} />
                              <span
                                style={{
                                  color: p.colorVar,
                                  fontSize: 11,
                                  fontWeight: 600,
                                }}
                              >
                                {p.name}
                              </span>
                              <span className="muted tt-up" style={{ fontSize: 9 }}>
                                {m.role ?? "msg"} · #{absoluteIdx + 1}
                              </span>
                            </div>
                            <p
                              style={{
                                fontSize: 11,
                                color: "var(--ink-1)",
                                margin: 0,
                                lineHeight: 1.5,
                              }}
                            >
                              {m.content ?? ""}
                            </p>
                          </div>
                        );
                      })
                  : ARGUS_DATA.TRANSCRIPT.slice(
                      Math.max(0, clampedScrub - 2),
                      clampedScrub,
                    ).map((m, i) => {
                      const p = ARGUS_DATA.PERSONAS.find((pp) => pp.id === m.persona);
                      if (!p) return null;
                      return (
                        <div
                          key={i}
                          style={{
                            marginBottom: 14,
                            paddingBottom: 14,
                            borderBottom: "1px solid var(--line-1)",
                          }}
                        >
                          <div
                            className="row gap-2"
                            style={{ alignItems: "center", marginBottom: 4 }}
                          >
                            <PersonaAvatar p={p} size={20} />
                            <span style={{ color: p.colorVar, fontSize: 11, fontWeight: 600 }}>
                              {p.name}
                            </span>
                            <span className="muted tt-up" style={{ fontSize: 9 }}>
                              R{m.roundN}·{m.round}
                            </span>
                          </div>
                          <p
                            style={{
                              fontSize: 11,
                              color: "var(--ink-1)",
                              margin: 0,
                              lineHeight: 1.5,
                            }}
                          >
                            {m.text}
                          </p>
                        </div>
                      );
                    })}
              </div>
            </div>
            <div className="grow col">
              <SectionHeader
                id="BRANCH"
                title="branch · inject TSMC fire"
                sub={`turn ${clampedScrub} · diverged at turn 4 · demo-only`}
              />
              <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
                <div
                  style={{
                    padding: 10,
                    marginBottom: 14,
                    borderLeft: "2px solid var(--green)",
                    background: "var(--green-glow)",
                  }}
                >
                  <div className="tt-up" style={{ fontSize: 9, color: "var(--green)" }}>
                    + FACT INJECTED at turn 4
                  </div>
                  <div style={{ fontSize: 11, color: "var(--ink-0)", marginTop: 4 }}>
                    &ldquo;Hsinchu Fab 18 fire reported, 6h estimated downtime, lithography section
                    affected&rdquo;
                  </div>
                </div>
                {ARGUS_DATA.PERSONAS[3] && (
                  <div
                    style={{
                      marginBottom: 14,
                      paddingBottom: 14,
                      borderBottom: "1px solid var(--line-1)",
                    }}
                  >
                    <div
                      className="row gap-2"
                      style={{ alignItems: "center", marginBottom: 4 }}
                    >
                      <PersonaAvatar p={ARGUS_DATA.PERSONAS[3]} size={20} />
                      <span
                        style={{
                          color: ARGUS_DATA.PERSONAS[3].colorVar,
                          fontSize: 11,
                          fontWeight: 600,
                        }}
                      >
                        {ARGUS_DATA.PERSONAS[3].name}
                      </span>
                      <Chip tone="green">DIVERGENT</Chip>
                    </div>
                    <p style={{ fontSize: 11, color: "var(--ink-1)", margin: 0, lineHeight: 1.5 }}>
                      This changes my prior calculation. A localized Fab 18 incident, even 6h,
                      intersects with the geopolitical timeline in ways markets cannot price...{" "}
                      <span style={{ color: "var(--green)" }}>[divergent reasoning continues]</span>
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div
            style={{
              padding: "10px 16px",
              borderTop: "1px solid var(--line-2)",
              display: "flex",
              gap: 12,
              alignItems: "center",
              background: "var(--bg-1)",
            }}
          >
            <Btn ghost onClick={() => setScrub((s) => Math.max(0, s - 1))}>
              ◀
            </Btn>
            <Btn ghost onClick={() => setScrub((s) => Math.min(totalLen, s + 1))}>
              ▶
            </Btn>
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              turn 0
            </span>
            <input
              type="range"
              min={0}
              max={totalLen}
              value={clampedScrub}
              onChange={(e) => setScrub(+e.target.value)}
              style={{ flex: 1, accentColor: "var(--amber)" }}
            />
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              {totalLen}
            </span>
            <span className="tab amber">turn {clampedScrub}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
