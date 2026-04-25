"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AsciiSpinner } from "@/components/ui/AsciiSpinner";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { CiteChip } from "@/components/ui/CiteChip";
import { Dot } from "@/components/ui/Dot";
import { Panel } from "@/components/ui/Panel";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Segmented } from "@/components/ui/Segmented";
import { useTypewriter } from "@/hooks/useTypewriter";
import { ARGUS_DATA, type Persona, type TranscriptMsg } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

function Message({
  m,
  p,
  stream,
  pById,
}: {
  m: TranscriptMsg;
  p: Persona;
  stream: boolean;
  pById: (id: string) => Persona | undefined;
}) {
  const display = useTypewriter(m.text, stream, 6);
  const isStreaming = stream && display.length < m.text.length;
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line-1)" }}>
      <div className="row gap-3" style={{ alignItems: "flex-start" }}>
        <PersonaAvatar p={p} size={28} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row gap-2" style={{ alignItems: "baseline", flexWrap: "wrap" }}>
            <span style={{ color: p.colorVar, fontWeight: 600, fontSize: 12 }}>{p.name}</span>
            <span className="tt-up muted" style={{ fontSize: 9 }}>
              {p.role}
            </span>
            <div style={{ flex: 1 }} />
            <span className="tab muted" style={{ fontSize: 9 }}>
              {m.t}
            </span>
            <Chip tone="amber" style={{ fontSize: 9 }}>
              R{m.roundN}·{m.round}
            </Chip>
          </div>
          {m.references && m.references.length > 0 && (() => {
            const ref = pById(m.references[0]);
            return ref ? (
              <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>
                ↪ replying to <span style={{ color: ref.colorVar }}>{ref.name}</span>
              </div>
            ) : null;
          })()}
          {m.challenge && (() => {
            const ch = pById(m.challenge);
            return ch ? (
              <div style={{ fontSize: 10, marginTop: 4, color: "var(--red)" }}>
                ⚠ challenging <span style={{ color: ch.colorVar }}>{ch.name}</span>
              </div>
            ) : null;
          })()}
          <div
            style={{
              fontSize: 13,
              color: "var(--ink-0)",
              marginTop: 6,
              lineHeight: 1.55,
              fontFamily: "'IBM Plex Sans', 'Inter', system-ui, sans-serif",
            }}
          >
            {display}
            {isStreaming && <span className="caret"></span>}
            {!isStreaming && (m.cites || []).map((c) => <CiteChip key={c.n} {...c} />)}
          </div>
          {!isStreaming && (
            <div className="row gap-3" style={{ marginTop: 8, alignItems: "center" }}>
              <Bar value={m.confidence} label="CONF" width={60} color="var(--green)" showVal />
              <span className="muted tt-up" style={{ fontSize: 9 }}>
                · {(m.cites || []).length} cite{(m.cites || []).length === 1 ? "" : "s"}
              </span>
              <div style={{ flex: 1 }} />
              <span className="muted" style={{ fontSize: 10, cursor: "pointer" }}>
                👍 ✕
              </span>
              <span className="muted" style={{ fontSize: 10, cursor: "pointer" }}>
                ⚠ challenge
              </span>
              <span className="muted" style={{ fontSize: 10, cursor: "pointer" }}>
                🔖 pin
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PersonaRefGraph({
  refs,
  personas,
}: {
  refs: [string, string][];
  personas: Persona[];
}) {
  const W = 280;
  const H = 200;
  const cx = W / 2;
  const cy = H / 2;
  const R = 70;
  const positions: Record<string, { x: number; y: number; p: Persona }> = {};
  personas.forEach((p, i) => {
    const a = (i / personas.length) * Math.PI * 2 - Math.PI / 2;
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
  const D = ARGUS_DATA;
  const T = D.TRANSCRIPT;
  const transcriptRef = useRef<HTMLDivElement>(null);

  const idx = useDebateStore((s) => s.idx);
  const advance = useDebateStore((s) => s.advance);
  const stepBack = useDebateStore((s) => s.stepBack);
  const paused = useDebateStore((s) => s.paused);
  const setPaused = useDebateStore((s) => s.setPaused);
  const speed = useDebateStore((s) => s.speed);
  const setSpeed = useDebateStore((s) => s.setSpeed);

  const [filterPersona, setFilterPersona] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (paused) return;
    if (idx >= T.length) return;
    const id = setTimeout(() => advance(T.length), 4200 / speed);
    return () => clearTimeout(id);
  }, [idx, paused, speed, T.length, advance]);

  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [idx]);

  const visible = T.slice(0, idx);
  const filtered = filterPersona ? visible.filter((m) => m.persona === filterPersona) : visible;
  const searched = search
    ? filtered.filter((m) => m.text.toLowerCase().includes(search.toLowerCase()))
    : filtered;

  const pById = (id: string) => D.PERSONAS.find((p) => p.id === id);

  const convergence = Math.min(0.78, (idx / T.length) * 0.78);
  const round = visible.length ? visible[visible.length - 1].round : "DRAFT";
  const roundN = visible.length ? visible[visible.length - 1].roundN : 1;

  const refs = useMemo(() => {
    const r: [string, string][] = [];
    visible.forEach((m) => {
      (m.references || []).forEach((to) => r.push([m.persona, to]));
      if (m.challenge) r.push([m.persona, m.challenge]);
    });
    return r;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="06·DEBATE"
        title="Debate Room"
        breadcrumb={`// d-2026-04-25-01 · "Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?"`}
        right={
          <div className="row gap-2">
            <Chip tone="amber">
              <Dot tone="amber" pulse /> ROUND {roundN} · {round}
            </Chip>
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
          <SectionHeader id="P" title="Cast" sub="7 personas" />
          <div className="col" style={{ overflowY: "auto" }}>
            {D.PERSONAS.map((p) => {
              const speaking = visible.length && visible[visible.length - 1].persona === p.id;
              const msgs = visible.filter((m) => m.persona === p.id).length;
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
                  <PersonaAvatar p={p} size={26} />
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
                      {p.flag} {msgs} msg{msgs === 1 ? "" : "s"}
                    </div>
                  </div>
                  {speaking ? <Dot tone="green" pulse /> : null}
                </div>
              );
            })}
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
              {searched.length} / {visible.length} msgs
            </span>
          </div>

          <div ref={transcriptRef} className="grow" style={{ overflowY: "auto", padding: "12px 0" }}>
            {searched.map((m, i) => {
              const p = pById(m.persona);
              if (!p) return null;
              const isLast = i === searched.length - 1 && idx <= T.length;
              const showStream = isLast && !paused;
              return (
                <Message
                  key={`${m.persona}-${i}-${m.t}`}
                  m={m}
                  p={p}
                  stream={showStream}
                  pById={pById}
                />
              );
            })}
            {!paused && idx < T.length && (
              <div style={{ padding: "8px 16px", fontSize: 10, color: "var(--ink-3)" }}>
                <AsciiSpinner /> awaiting next turn...
              </div>
            )}
            {idx >= T.length && (
              <div
                style={{
                  padding: 24,
                  textAlign: "center",
                  color: "var(--ink-2)",
                  fontSize: 11,
                }}
              >
                ─── debate concluded · synthesizer engaged ───
                <div style={{ marginTop: 12 }}>
                  <Btn primary onClick={() => router.push("/synthesis")}>
                    VIEW SYNTHESIS →
                  </Btn>
                </div>
              </div>
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
            <PersonaRefGraph refs={refs} personas={D.PERSONAS} />
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
