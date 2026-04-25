// argus — Agent Ops Theater, Persona Designer, Debate Room
const { useState: ux, useEffect: ue, useMemo: um, useRef: ur } = React;

// ─────────────────────────────────────────────
// AGENT OPS THEATER — orchestration mission control
// ─────────────────────────────────────────────
function OpsTheater({ setRoute, debateState }) {
  const D = window.ARGUS_DATA;
  const [tick, setTick] = ux(0);
  const [sel, setSel] = ux(null);
  const [paused, setPaused] = ux(false);

  ue(() => {
    if (paused) return;
    const id = setInterval(() => setTick(t => t + 1), 600);
    return () => clearInterval(id);
  }, [paused]);

  const W = 1000, H = 560;
  const stateColor = { idle: "var(--ink-3)", thinking: "var(--amber)", "tool-call": "var(--cyan)", speaking: "var(--green)", running: "var(--green)" };

  // simulate live activity
  const personaActivity = D.PERSONAS.map((p, i) => ({
    p,
    cpu: 30 + ((tick + i * 3) % 70),
    tokens: 1240 + ((tick * 7 + i * 100) % 800),
    state: D.ORCHESTRATION.find(o => o.id === `p-${p.id.replace("indopacom","indo").replace("analyst","analyst").replace("ishiba","ishiba")}`)?.state || "idle",
  }));

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="04·OPS" title="Agent Ops Theater"
        breadcrumb="// run d-2026-04-25-01 · Taiwan Strait quarantine · 7 personas"
        right={<div className="row gap-2">
          <Btn ghost active={!paused} onClick={() => setPaused(false)}>▶ LIVE</Btn>
          <Btn ghost active={paused} onClick={() => setPaused(true)}>⏸ PAUSE</Btn>
          <Btn ghost>↺ STEP</Btn>
          <Btn ghost>◐ SLOW-MO</Btn>
          <Btn primary onClick={() => setRoute("debate")}>OPEN DEBATE ROOM →</Btn>
        </div>}
      />

      <div className="grow row" style={{ overflow: "hidden" }}>
        {/* Orchestration graph */}
        <div className="grow col" style={{ borderRight: "1px solid var(--line-2)", overflow: "hidden" }}>
          <div className="grow grid-bg" style={{ position: "relative" }}>
            <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%" }} preserveAspectRatio="xMidYMid meet">
              {/* swimlane labels */}
              <text x={20} y={48} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">INGEST</text>
              <text x={W*0.24 - 28} y={48} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">RESEARCH</text>
              <text x={W*0.45 - 50} y={48} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">ORCHESTRATION</text>
              <text x={W*0.66 - 38} y={48} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">PERSONAS · 7</text>
              <text x={W*0.88 - 38} y={48} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">SYNTHESIZER</text>

              {/* swimlane dividers */}
              {[0.16, 0.34, 0.55, 0.78].map(x => (
                <line key={x} x1={x*W} y1={20} x2={x*W} y2={H-20} stroke="var(--line-1)" strokeDasharray="3 5" />
              ))}

              {/* edges with animated dashes */}
              {D.ORCHESTRATION.flatMap(node =>
                node.outEdges.map(toId => {
                  const to = D.ORCHESTRATION.find(n => n.id === toId);
                  if (!to) return null;
                  const x1 = node.x * W, y1 = node.y * H;
                  const x2 = to.x * W, y2 = to.y * H;
                  const active = node.state !== "idle" && to.state !== "idle";
                  return (
                    <g key={`${node.id}-${toId}`}>
                      <line x1={x1} y1={y1} x2={x2} y2={y2}
                        stroke={active ? "var(--amber)" : "var(--line-2)"}
                        strokeWidth={active ? 1 : 0.5}
                        strokeDasharray={active ? "4 4" : "0"}
                        opacity={active ? 0.8 : 0.5}>
                        {active && <animate attributeName="stroke-dashoffset" from="0" to="-16" dur="0.6s" repeatCount="indefinite" />}
                      </line>
                    </g>
                  );
                })
              )}

              {/* nodes */}
              {D.ORCHESTRATION.map(n => {
                const x = n.x * W, y = n.y * H;
                const c = stateColor[n.state];
                const isPersona = n.id.startsWith("p-");
                const w = isPersona ? 92 : 110;
                const h = 32;
                return (
                  <g key={n.id} style={{ cursor: "pointer" }} onClick={() => setSel(n)}>
                    <rect x={x - w/2} y={y - h/2} width={w} height={h}
                      fill="var(--bg-2)" stroke={c} strokeWidth="1" />
                    <text x={x} y={y - 2} fontFamily="JetBrains Mono" fontSize="10" fill="var(--ink-0)" textAnchor="middle" fontWeight="600">{n.label}</text>
                    <text x={x} y={y + 9} fontFamily="JetBrains Mono" fontSize="8" fill={c} textAnchor="middle">
                      {n.state === "thinking" ? "◐ thinking" : n.state === "tool-call" ? "▸ tool" : n.state === "speaking" ? "◉ speak" : "○ idle"}
                    </text>
                    {n.state !== "idle" && (
                      <circle cx={x + w/2 - 6} cy={y - h/2 + 6} r="2.5" fill={c}>
                        <animate attributeName="opacity" from="1" to="0.3" dur="1s" repeatCount="indefinite" />
                      </circle>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* tape at bottom — system events */}
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, background: "var(--bg-2)", borderTop: "1px solid var(--line-2)", height: 78, overflow: "hidden", padding: "6px 12px" }}>
              <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 4 }}>SYSTEM EVENT TAPE · realtime</div>
              <div style={{ fontSize: 10, lineHeight: 1.5, color: "var(--ink-1)", fontFamily: "JetBrains Mono" }}>
                <div><span className="tab muted">14:22:08.412</span> <span className="green">orchestrator</span> &gt; cast 7 personas; depth=deep; turn-limit=14</div>
                <div><span className="tab muted">14:22:08.821</span> <span className="amber">p-indopacom</span> &gt; tool_call(kg.path("us","tw")) → 4 paths</div>
                <div><span className="tab muted">14:22:09.114</span> <span className="cyan">p-analyst</span> &gt; memory_write key="quarantine.prob" val=0.42</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: persona activity strips + resources */}
        <div className="col" style={{ width: 360, overflow: "hidden" }}>
          <Panel id="R1" title="Resource Meter" sub="last 60s" style={{ flexShrink: 0 }}>
            <div style={{ padding: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>TOK / MIN</div>
                <div className="tab" style={{ fontSize: 22, color: "var(--amber)", fontWeight: 600 }}>14,281</div>
                <Sparkline data={[8,12,9,14,18,16,22,19,25,21,24,28,26,24,22,28,31,28]} width={140} height={24} />
              </div>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>COST / RUN</div>
                <div className="tab" style={{ fontSize: 22, color: "var(--ink-0)", fontWeight: 600 }}>$0.31</div>
                <Sparkline data={[2,3,2,4,5,4,6,5,7,6,7,8,7,7,6,8,9,8]} width={140} height={24} color="var(--green)" />
              </div>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>QUEUE</div>
                <div className="tab" style={{ fontSize: 14, color: "var(--ink-0)" }}>3 / 16</div>
              </div>
              <div>
                <div className="tt-up muted" style={{ fontSize: 9 }}>ERRORS 1H</div>
                <div className="tab" style={{ fontSize: 14, color: "var(--green)" }}>0</div>
              </div>
            </div>
            <div style={{ padding: "0 14px 14px" }}>
              <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 4 }}>MODEL MIX</div>
              <div style={{ display: "flex", height: 8, border: "1px solid var(--line-2)" }}>
                <div style={{ width: "42%", background: "var(--p-3)" }} title="Sonnet" />
                <div style={{ width: "31%", background: "var(--amber)" }} title="Opus" />
                <div style={{ width: "27%", background: "var(--p-2)" }} title="Haiku" />
              </div>
              <div className="row" style={{ fontSize: 9, marginTop: 4, color: "var(--ink-2)", justifyContent: "space-between" }}>
                <span>SONNET 42%</span><span>OPUS 31%</span><span>HAIKU 27%</span>
              </div>
            </div>
          </Panel>

          <Panel id="R2" title="Persona Activity" sub="live · thought / tool / speak" style={{ flex: 1 }}>
            <div className="col" style={{ overflowY: "auto" }}>
              {personaActivity.map(({p, cpu, tokens, state}, i) => (
                <div key={p.id} style={{ padding: "10px 12px", borderBottom: "1px solid var(--line-1)" }}>
                  <div className="row gap-2" style={{ alignItems: "center" }}>
                    <PersonaAvatar p={p} size={20} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, color: "var(--ink-0)" }}>{p.name}</div>
                      <div style={{ fontSize: 9, color: "var(--ink-2)" }}>{p.model}</div>
                    </div>
                    <span className="tt-up" style={{ fontSize: 9, color: stateColor[state] }}>
                      {state === "idle" ? "○ idle" : state === "thinking" ? "◐ think" : state === "tool-call" ? "▸ tool" : "◉ speak"}
                    </span>
                  </div>
                  <div className="row gap-2" style={{ marginTop: 6, alignItems: "center" }}>
                    <Bar value={cpu} max={100} width={140} color={p.colorVar} />
                    <span className="tab muted" style={{ fontSize: 9 }}>{tokens} tok</span>
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

// ─────────────────────────────────────────────
// PERSONA DESIGNER
// ─────────────────────────────────────────────
function PersonaDesigner() {
  const D = window.ARGUS_DATA;
  const [sel, setSel] = ux(D.PERSONAS[0]);
  const [edit, setEdit] = ux(null);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="05·PERSONAS" title="Persona Designer"
        breadcrumb={`// 7 cast · auto-balance enabled`}
        right={<div className="row gap-2">
          <Btn ghost>+ ADD PERSONA</Btn>
          <Btn ghost>◫ TEMPLATE LIBRARY</Btn>
          <Btn ghost>◐ AUTO-BALANCE</Btn>
          <Btn primary>SAVE CAST →</Btn>
        </div>}
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        {/* Left: cards grid */}
        <div className="grow col" style={{ overflow: "hidden", padding: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12, overflowY: "auto", paddingRight: 4 }}>
            {D.PERSONAS.map(p => {
              const isSel = sel?.id === p.id;
              return (
                <div key={p.id}
                  onClick={() => setSel(p)}
                  className={`panel bd-${p.color}`}
                  style={{
                    padding: 14, cursor: "pointer", display: "flex", flexDirection: "column", gap: 10,
                    borderColor: isSel ? p.colorVar : "var(--line-2)",
                    borderWidth: isSel ? 2 : 1,
                    borderStyle: "solid",
                    background: isSel ? "var(--bg-3)" : "var(--bg-2)",
                  }}>
                  <div className="row gap-3" style={{ alignItems: "flex-start" }}>
                    <PersonaAvatar p={p} size={42} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600 }}>{p.name}</div>
                      <div style={{ fontSize: 11, color: "var(--ink-1)" }}>{p.role}</div>
                      <div className="tt-up" style={{ fontSize: 9, color: p.colorVar, marginTop: 2 }}>{p.flag} {p.country} · {p.model}</div>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--ink-3)", cursor: "pointer" }}>⋯</span>
                  </div>
                  <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>BIAS</div>
                  <div style={{ fontSize: 11, color: "var(--ink-1)", lineHeight: 1.4 }}>{p.bias}</div>
                  <div className="row gap-3">
                    <div style={{ flex: 1 }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>TEMP</span>
                      <Bar value={p.temperature} color={p.colorVar} width={"100%"} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>AGGR</span>
                      <Bar value={p.aggression} color="var(--red)" width={"100%"} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>CITE</span>
                      <Bar value={p.citationStrictness} color="var(--green)" width={"100%"} />
                    </div>
                  </div>
                  <div className="row gap-2">
                    {p.beliefs.slice(0,2).map((b,i) => <Chip key={i}>{b}</Chip>)}
                  </div>
                </div>
              );
            })}
            {/* Add card */}
            <div style={{ border: "1px dashed var(--line-3)", padding: 14, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--ink-3)", fontSize: 11, minHeight: 200, cursor: "pointer" }}>
              <div style={{ fontSize: 22, marginBottom: 8 }}>+</div>
              <div className="tt-up">ADD PERSONA</div>
              <div style={{ fontSize: 10, marginTop: 4, textAlign: "center" }}>auto-balance suggests:<br/><span style={{ color: "var(--amber)" }}>EU diplomat · KR security analyst</span></div>
            </div>
          </div>
        </div>

        {/* Right: detail / edit */}
        <div className="col" style={{ width: 380, borderLeft: "1px solid var(--line-2)", background: "var(--bg-1)", overflowY: "auto" }}>
          {sel && (
            <>
              <div style={{ padding: 16, borderBottom: "1px solid var(--line-2)", background: "var(--bg-2)" }}>
                <div className="row gap-3" style={{ alignItems: "flex-start" }}>
                  <PersonaAvatar p={sel} size={48} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 16, color: "var(--ink-0)", fontWeight: 600 }}>{sel.name}</div>
                    <div style={{ fontSize: 11, color: "var(--ink-1)" }}>{sel.role}</div>
                    <div className="tt-up" style={{ fontSize: 9, color: sel.colorVar, marginTop: 4 }}>{sel.flag} {sel.country}</div>
                  </div>
                </div>
              </div>

              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}>SYSTEM PROMPT · 1.4k tok</div>
                <div style={{ background: "var(--bg-0)", padding: 10, fontSize: 10, fontFamily: "JetBrains Mono", color: "var(--ink-1)", lineHeight: 1.5, border: "1px solid var(--line-1)", maxHeight: 150, overflowY: "auto" }}>
                  You are <span style={{ color: sel.colorVar }}>{sel.name}</span>, {sel.role}. Speak from this position with the tone, priorities, and constraints the role implies. Reference your stated beliefs. When you cite, prefer primary sources from your nation/institution. You may reference the shared world state but must hold your own institutional memory. Constitution: {sel.redlines.length} red-line{sel.redlines.length===1?"":"s"} enforced.
                </div>
                <Btn ghost style={{ marginTop: 8 }}>EDIT PROMPT</Btn>
              </div>

              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}>BELIEFS</div>
                {sel.beliefs.map((b, i) => (
                  <div key={i} style={{ padding: "4px 0", fontSize: 11, color: "var(--ink-1)", display: "flex", gap: 6 }}>
                    <span style={{ color: sel.colorVar }}>·</span>
                    <span style={{ flex: 1 }}>{b}</span>
                  </div>
                ))}
              </div>

              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--red)", marginBottom: 8 }}>RED LINES · constitution</div>
                {sel.redlines.length === 0 ? (
                  <div className="muted" style={{ fontSize: 10 }}>none — observer persona</div>
                ) : sel.redlines.map((r, i) => (
                  <div key={i} style={{ padding: "4px 0", fontSize: 11, color: "var(--ink-1)" }}>⊘ {r}</div>
                ))}
              </div>

              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}>TUNING</div>
                <SliderRow label="Temperature" value={sel.temperature} color={sel.colorVar} />
                <SliderRow label="Aggression" value={sel.aggression} color="var(--red)" />
                <SliderRow label="Citation strict." value={sel.citationStrictness} color="var(--green)" />
              </div>

              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}>TOOL ACCESS</div>
                {[
                  ["kg.search", true], ["kg.path", true], ["search.web", true],
                  ["memory.read", true], ["memory.write", true], ["summon.persona", false],
                ].map(([t, on], i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0", fontSize: 11 }}>
                    <span style={{ color: on ? "var(--green)" : "var(--ink-3)" }}>{on ? "■" : "□"}</span>
                    <span style={{ color: on ? "var(--ink-0)" : "var(--ink-3)" }}>{t}</span>
                  </div>
                ))}
              </div>

              <div style={{ padding: 14 }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}>MEMORY · {sel.memorySize}</div>
                <KV k="Persistence" v="across-debate" />
                <KV k="Embeddings" v="text-3-large" />
                <KV k="Decay" v="exp(−t/30d)" />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SliderRow({ label, value, color }) {
  return (
    <div style={{ padding: "5px 0" }}>
      <div className="row gap-2" style={{ alignItems: "center" }}>
        <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 110 }}>{label}</span>
        <div style={{ flex: 1, height: 4, background: "var(--bg-3)", border: "1px solid var(--line-1)", position: "relative" }}>
          <div style={{ width: `${value*100}%`, height: "100%", background: color }} />
          <div style={{ position: "absolute", left: `${value*100}%`, top: -3, width: 2, height: 10, background: "var(--ink-0)", transform: "translateX(-1px)" }} />
        </div>
        <span className="tab" style={{ fontSize: 10, color: "var(--ink-1)", minWidth: 32, textAlign: "right" }}>{value.toFixed(2)}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// DEBATE ROOM — live transcript + persona graph + world state
// ─────────────────────────────────────────────
function DebateRoom({ setRoute, debateState, setDebateState }) {
  const D = window.ARGUS_DATA;
  const T = D.TRANSCRIPT;
  const transcriptRef = ur(null);

  const [speed, setSpeed] = ux(1);
  const [paused, setPaused] = ux(false);
  const [filterPersona, setFilterPersona] = ux(null);
  const [search, setSearch] = ux("");

  // Auto-advance through messages
  ue(() => {
    if (paused) return;
    if (debateState.idx >= T.length) return;
    const id = setTimeout(() => {
      setDebateState(s => ({ ...s, idx: Math.min(T.length, s.idx + 1) }));
    }, 4200 / speed);
    return () => clearTimeout(id);
  }, [debateState.idx, paused, speed]);

  ue(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [debateState.idx]);

  const visible = T.slice(0, debateState.idx);
  const filtered = filterPersona ? visible.filter(m => m.persona === filterPersona) : visible;
  const searched = search ? filtered.filter(m => m.text.toLowerCase().includes(search.toLowerCase())) : filtered;

  const pById = (id) => D.PERSONAS.find(p => p.id === id);

  // Convergence — fake measure based on idx
  const convergence = Math.min(0.78, debateState.idx / T.length * 0.78);
  const round = visible.length ? visible[visible.length - 1].round : "DRAFT";
  const roundN = visible.length ? visible[visible.length - 1].roundN : 1;

  // Persona reference graph
  const refs = useMemo(() => {
    const r = [];
    visible.forEach(m => {
      (m.references || []).forEach(to => r.push([m.persona, to]));
      if (m.challenge) r.push([m.persona, m.challenge]);
    });
    return r;
  }, [debateState.idx]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="06·DEBATE" title="Debate Room"
        breadcrumb={`// d-2026-04-25-01 · "Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?"`}
        right={<div className="row gap-2">
          <Chip tone="amber"><Dot tone="amber" pulse /> ROUND {roundN} · {round}</Chip>
          <Btn ghost active={paused} onClick={() => setPaused(!paused)}>{paused ? "▶ RESUME" : "⏸ PAUSE"}</Btn>
          <Btn ghost onClick={() => setDebateState(s => ({...s, idx: Math.max(0, s.idx - 1)}))}>↶ STEP BACK</Btn>
          <Segmented size="sm" options={[{value:0.5,label:"0.5×"},{value:1,label:"1×"},{value:2,label:"2×"},{value:4,label:"4×"}]} value={speed} onChange={setSpeed} />
          <Btn primary onClick={() => setRoute("synthesis")}>VIEW SYNTHESIS →</Btn>
        </div>}
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        {/* LEFT: Personas in this debate */}
        <div className="col" style={{ width: 220, borderRight: "1px solid var(--line-2)", background: "var(--bg-1)", overflow: "hidden" }}>
          <SectionHeader id="P" title="Cast" sub="7 personas" />
          <div className="col" style={{ overflowY: "auto" }}>
            {D.PERSONAS.map(p => {
              const speaking = visible.length && visible[visible.length-1].persona === p.id;
              const msgs = visible.filter(m => m.persona === p.id).length;
              const isFilter = filterPersona === p.id;
              return (
                <div key={p.id}
                  onClick={() => setFilterPersona(isFilter ? null : p.id)}
                  style={{
                    padding: "10px 12px", borderBottom: "1px solid var(--line-1)",
                    cursor: "pointer", display: "flex", gap: 8, alignItems: "center",
                    background: isFilter ? "var(--bg-3)" : speaking ? "var(--bg-3)" : "transparent",
                    borderLeft: isFilter ? `2px solid ${p.colorVar}` : speaking ? `2px solid var(--amber)` : "2px solid transparent",
                  }}
                >
                  <PersonaAvatar p={p} size={26} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, color: "var(--ink-0)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</div>
                    <div style={{ fontSize: 9, color: "var(--ink-2)" }}>{p.flag} {msgs} msg{msgs===1?"":"s"}</div>
                  </div>
                  {speaking && <Dot tone="green" pulse />}
                </div>
              );
            })}
          </div>
          <div style={{ padding: 12, borderTop: "1px solid var(--line-2)" }}>
            <Btn ghost style={{ width: "100%" }}>+ SUMMON PERSONA</Btn>
          </div>
        </div>

        {/* CENTER: transcript */}
        <div className="col grow" style={{ overflow: "hidden", background: "var(--bg-0)" }}>
          {/* search / filter */}
          <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--line-2)", display: "flex", gap: 8, alignItems: "center", background: "var(--bg-1)" }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="search transcript / regex..."
              className="input"
              style={{ flex: 1, fontSize: 11, padding: "4px 8px" }}
            />
            {filterPersona && (
              <Chip tone="amber" style={{ cursor: "pointer" }}>
                <span onClick={() => setFilterPersona(null)}>filter: {pById(filterPersona).initials} ✕</span>
              </Chip>
            )}
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              {searched.length} / {visible.length} msgs
            </span>
          </div>

          {/* transcript */}
          <div ref={transcriptRef} className="grow" style={{ overflowY: "auto", padding: "12px 0" }}>
            {searched.map((m, i) => {
              const p = pById(m.persona);
              const isLast = i === searched.length - 1 && debateState.idx <= T.length;
              const showStream = isLast && !paused;
              return <Message key={`${m.persona}-${i}-${m.t}`} m={m} p={p} stream={showStream} pById={pById} />;
            })}
            {!paused && debateState.idx < T.length && (
              <div style={{ padding: "8px 16px", fontSize: 10, color: "var(--ink-3)" }}>
                <AsciiSpinner /> awaiting next turn...
              </div>
            )}
            {debateState.idx >= T.length && (
              <div style={{ padding: 24, textAlign: "center", color: "var(--ink-2)", fontSize: 11 }}>
                ─── debate concluded · synthesizer engaged ───
                <div style={{ marginTop: 12 }}>
                  <Btn primary onClick={() => setRoute("synthesis")}>VIEW SYNTHESIS →</Btn>
                </div>
              </div>
            )}
          </div>

          {/* moderator nudge bar */}
          <div style={{ borderTop: "1px solid var(--line-2)", padding: 10, background: "var(--bg-1)", display: "flex", gap: 8, alignItems: "center" }}>
            <span className="tt-up muted" style={{ fontSize: 9 }}>MODERATOR</span>
            <Btn ghost>+ INJECT FACT</Btn>
            <Btn ghost>⚠ CHALLENGE LAST</Btn>
            <Btn ghost>↺ FORCE REBUT</Btn>
            <div style={{ flex: 1 }} />
            <span className="muted tt-up" style={{ fontSize: 9 }}>BUDGET</span>
            <span className="tab amber" style={{ fontSize: 11 }}>$0.31 / $1.00</span>
          </div>
        </div>

        {/* RIGHT: world state + convergence + persona graph */}
        <div className="col" style={{ width: 320, borderLeft: "1px solid var(--line-2)", background: "var(--bg-1)", overflow: "hidden" }}>
          <Panel id="C" title="Convergence" sub={`round ${roundN}/4`} style={{ flexShrink: 0 }}>
            <div style={{ padding: 14 }}>
              <div className="row gap-2" style={{ alignItems: "baseline" }}>
                <span className="tab" style={{ fontSize: 28, color: "var(--amber)", fontWeight: 600 }}>{(convergence * 100).toFixed(0)}</span>
                <span className="muted">/100</span>
                <div style={{ flex: 1 }} />
                <Chip tone="amber">{convergence > 0.6 ? "CONVERGING" : convergence > 0.3 ? "DIVERGING" : "OPENING"}</Chip>
              </div>
              <Bar value={convergence} width={"100%"} height={6} color="var(--amber)" />
              <div className="row" style={{ fontSize: 9, marginTop: 4, color: "var(--ink-2)", justifyContent: "space-between" }}>
                <span>DRAFT</span><span>CRITIQUE</span><span>REBUT</span><span>VOTE</span>
              </div>
            </div>
          </Panel>

          <Panel id="G" title="Reference Graph" sub="who-cites-whom" style={{ flexShrink: 0, height: 220 }}>
            <PersonaRefGraph refs={refs} personas={D.PERSONAS} />
          </Panel>

          <Panel id="W" title="World State" sub="kg snapshot · Δ this round" style={{ flex: 1 }}>
            <div className="col" style={{ overflowY: "auto", padding: 12, gap: 10 }}>
              <div>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--green)", marginBottom: 4 }}>+ ENTITIES THIS ROUND</div>
                <div style={{ fontSize: 10, color: "var(--ink-1)", lineHeight: 1.6 }}>
                  · Bashi Channel <span className="muted">(place)</span><br/>
                  · Hellscape concept <span className="muted">(doctrine)</span><br/>
                  · Yonaguni Island <span className="muted">(place)</span><br/>
                  · ROCS Hai Kun <span className="muted">(asset)</span>
                </div>
              </div>
              <div>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--amber)", marginBottom: 4 }}>~ EDGES UPDATED (4)</div>
                <div style={{ fontSize: 10, color: "var(--ink-1)", lineHeight: 1.6 }}>
                  · pla → bashi · transit-density 0.6→0.9<br/>
                  · jp → tw · linkage strength 0.7→0.9<br/>
                  · indopacom → bashi · posture: contested<br/>
                  · tsmc → fab21 · status: insurance
                </div>
              </div>
              <div>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 4 }}>SOURCES TOUCHED</div>
                <div className="row gap-1" style={{ flexWrap: "wrap" }}>
                  {["GDELT","Reuters","Xinhua","CSIS","RAND","DoD","UNCLOS","BIS","ESC-TW"].map(s => <Chip key={s}>{s}</Chip>)}
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Message({ m, p, stream, pById }) {
  const display = useTypewriter(m.text, stream, 6);
  const isStreaming = stream && display.length < m.text.length;
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line-1)" }}>
      <div className="row gap-3" style={{ alignItems: "flex-start" }}>
        <PersonaAvatar p={p} size={28} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row gap-2" style={{ alignItems: "baseline", flexWrap: "wrap" }}>
            <span style={{ color: p.colorVar, fontWeight: 600, fontSize: 12 }}>{p.name}</span>
            <span className="tt-up muted" style={{ fontSize: 9 }}>{p.role}</span>
            <div style={{ flex: 1 }} />
            <span className="tab muted" style={{ fontSize: 9 }}>{m.t}</span>
            <Chip tone="amber" style={{ fontSize: 9 }}>R{m.roundN}·{m.round}</Chip>
          </div>
          {m.references && m.references.length > 0 && (
            <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>
              ↪ replying to <span style={{ color: pById(m.references[0]).colorVar }}>{pById(m.references[0]).name}</span>
            </div>
          )}
          {m.challenge && (
            <div style={{ fontSize: 10, marginTop: 4, color: "var(--red)" }}>
              ⚠ challenging <span style={{ color: pById(m.challenge).colorVar }}>{pById(m.challenge).name}</span>
            </div>
          )}
          <div style={{
            fontSize: 13, color: "var(--ink-0)", marginTop: 6, lineHeight: 1.55,
            fontFamily: "'IBM Plex Sans', 'Inter', system-ui, sans-serif",
          }}>
            {display}
            {isStreaming && <span className="caret"></span>}
            {!isStreaming && (m.cites || []).map(c => <CiteChip key={c.n} {...c} />)}
          </div>
          {!isStreaming && (
            <div className="row gap-3" style={{ marginTop: 8, alignItems: "center" }}>
              <Bar value={m.confidence} label="CONF" width={60} color="var(--green)" showVal />
              <span className="muted tt-up" style={{ fontSize: 9 }}>· {(m.cites||[]).length} cite{(m.cites||[]).length===1?"":"s"}</span>
              <div style={{ flex: 1 }} />
              <span className="muted" style={{ fontSize: 10, cursor: "pointer" }}>👍 ✕</span>
              <span className="muted" style={{ fontSize: 10, cursor: "pointer" }}>⚠ challenge</span>
              <span className="muted" style={{ fontSize: 10, cursor: "pointer" }}>🔖 pin</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PersonaRefGraph({ refs, personas }) {
  const W = 280, H = 200;
  const cx = W / 2, cy = H / 2;
  const R = 70;
  const positions = personas.reduce((acc, p, i) => {
    const a = (i / personas.length) * Math.PI * 2 - Math.PI / 2;
    acc[p.id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a), p };
    return acc;
  }, {});
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%" }} preserveAspectRatio="xMidYMid meet">
      {refs.map(([from, to], i) => {
        const a = positions[from], b = positions[to];
        if (!a || !b) return null;
        return (
          <g key={i}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={a.p.colorVar} strokeWidth="0.8" opacity="0.6" markerEnd="url(#arrow)" />
          </g>
        );
      })}
      <defs>
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="var(--ink-2)" />
        </marker>
      </defs>
      {Object.values(positions).map(({x,y,p}) => (
        <g key={p.id}>
          <circle cx={x} cy={y} r="11" fill="var(--bg-2)" stroke={p.colorVar} strokeWidth="1.5" />
          <text x={x} y={y+3} fontSize="8" fill={p.colorVar} fontFamily="JetBrains Mono" textAnchor="middle" fontWeight="600">{p.initials}</text>
        </g>
      ))}
    </svg>
  );
}

Object.assign(window, { OpsTheater, PersonaDesigner, DebateRoom });
