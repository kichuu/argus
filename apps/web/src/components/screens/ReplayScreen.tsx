"use client";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockBadge } from "@/components/ui/MockBadge";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  api,
  type DiscussionMessage,
  type DiscussionSummary,
  type PersonaSummary,
} from "@/lib/api";
import type { Persona } from "@/mock/data";

// NOTE: branches are demo-only — there is no persistence layer for them yet,
// so the SVG branch tree and the right-hand "branch · inject TSMC fire" panel
// remain mock data even when the main timeline is live.
const BRANCHES = [
  { id: "main", label: "main", color: "var(--amber)", events: [0, 2, 4, 6, 8, 10, 12], current: true },
  { id: "b1", label: "branch · inject TSMC fire", color: "var(--p-2)", events: [4, 6, 8] },
  { id: "b2", label: "branch · swap Lai → Hou Yu-ih", color: "var(--p-4)", events: [2, 4, 6, 8] },
  { id: "b3", label: "branch · add EU persona", color: "var(--p-3)", events: [6, 8, 10, 11] },
];

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

// PersonaAvatar reads only `colorVar` and `initials`; we synthesize a Persona-shaped
// object so we don't have to retouch the avatar component.
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

export function ReplayScreen() {
  const discussionsQuery = useQuery({
    queryKey: ["recent-discussions"],
    queryFn: api.discussions,
    staleTime: 60_000,
    retry: 0,
  });

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
  const totalLen = liveMessages.length;

  const [scrub, setScrub] = useState(0);

  const clampedScrub = Math.min(Math.max(scrub, 0), Math.max(totalLen, 0));
  const effectiveScrub = totalLen > 0 && scrub === 0 ? Math.min(8, totalLen) : clampedScrub;

  const lookupPersona = (m: DiscussionMessage): LivePersona | null => {
    const id = m.persona_id ?? m.agent_id;
    if (!id) return null;
    return personaMap.get(id) ?? null;
  };

  if (isLoading) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader code="09·REPLAY" title="Replay & Branch" breadcrumb="// loading…" />
        <Skeleton rows={10} rowHeight={20} style={{ padding: 24 }} />
      </div>
    );
  }

  if (!apiOnline) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader
          code="09·REPLAY"
          title="Replay & Branch"
          breadcrumb="// no completed debates"
          right={
            <div className="row gap-2" style={{ alignItems: "center" }}>
              <MockBadge online={false} loading={false} />
            </div>
          }
        />
        <div style={{ padding: 24 }}>
          <EmptyState
            title="No completed debates yet"
            hint="Once a debate finishes, you'll be able to replay and branch from any turn here."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="09·REPLAY"
        title="Replay & Branch"
        breadcrumb={`// ${recent?.id ?? "—"} · scrubbing turn ${effectiveScrub}/${totalLen} · ${BRANCHES.length} branches (demo)`}
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
              <div className="row gap-2" style={{ alignItems: "center" }}>
                <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
                  BRANCH TREE
                </span>
                <Chip tone="amber">demo</Chip>
              </div>
              <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                branches are demo-only — no persistence layer yet
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
                      {b.id !== "main" ? " (demo)" : ""}
                    </text>
                    {b.events.map((eIdx, i) => {
                      const x = 60 + eIdx * 70;
                      const isScrub = b.current && eIdx === effectiveScrub - 1;
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
                title={`main · ${recent?.id ?? ""}`}
                sub={`turn ${effectiveScrub}`}
              />
              <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
                {liveMessages
                  .slice(Math.max(0, effectiveScrub - 2), effectiveScrub)
                  .map((m, i) => {
                    const absoluteIdx = Math.max(0, effectiveScrub - 2) + i;
                    const p = lookupPersona(m);
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
                          {p && <PersonaAvatar p={avatarPersona(p)} size={20} />}
                          <span
                            style={{
                              color: p?.colorVar ?? "var(--ink-0)",
                              fontSize: 11,
                              fontWeight: 600,
                            }}
                          >
                            {p?.name ?? m.persona_id ?? m.agent_id ?? "agent"}
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
                  })}
              </div>
            </div>
            <div className="grow col">
              <SectionHeader
                id="BRANCH"
                title="branch · inject TSMC fire"
                sub={`turn ${effectiveScrub} · diverged at turn 4 · demo-only`}
                right={<Chip tone="amber">demo</Chip>}
              />
              <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
                <div
                  className="row gap-2"
                  style={{ alignItems: "center", marginBottom: 10 }}
                >
                  <Chip tone="amber">demo</Chip>
                  <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                    no persistence layer yet — illustrative diff only
                  </span>
                </div>
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
                <div
                  style={{
                    padding: 12,
                    border: "1px dashed var(--line-2)",
                    background: "var(--bg-1)",
                  }}
                >
                  <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
                    branch reasoning preview
                  </div>
                  <p style={{ fontSize: 11, color: "var(--ink-2)", margin: 0, lineHeight: 1.5 }}>
                    Once branch persistence ships, this panel will replay divergent agent
                    reasoning starting from the injected fact. For now, it&apos;s a placeholder
                    to communicate the shape of the feature.
                  </p>
                </div>
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
              value={effectiveScrub}
              onChange={(e) => setScrub(+e.target.value)}
              style={{ flex: 1, accentColor: "var(--amber)" }}
            />
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              {totalLen}
            </span>
            <span className="tab amber">turn {effectiveScrub}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
