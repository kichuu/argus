// argus — Synthesis View, Synthesis Library, Source Monitor, Replay & Branch, Observability, Compare, Settings
const { useState: us3, useEffect: ue3, useMemo: um3 } = React;

// ─────────────────────────────────────────────
// SYNTHESIS VIEW
// ─────────────────────────────────────────────
function SynthesisView({ setRoute }) {
  const D = window.ARGUS_DATA;
  const S = D.SYNTHESIS;
  const pById = (id) => D.PERSONAS.find(p => p.id === id);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="07·SYNTH" title="Synthesis"
        breadcrumb={`// d-2026-04-25-01 · 7 personas · 13 turns · 1m 42s · ${S.evidence} citations`}
        right={<div className="row gap-2">
          <Btn ghost>↺ RE-RUN</Btn>
          <Btn ghost>⌥ COUNTERFACTUAL</Btn>
          <Btn ghost>↗ EXPORT</Btn>
          <Btn ghost>⎘ SHARE</Btn>
          <Btn primary>+ SUBSCRIBE</Btn>
        </div>}
      />

      <div className="grow" style={{ overflowY: "auto" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: 24, display: "grid", gridTemplateColumns: "1fr 360px", gap: 20 }}>
          {/* MAIN COLUMN */}
          <div className="col gap-4">
            {/* Consensus */}
            <div className="panel" style={{ padding: 24, borderLeft: "3px solid var(--amber)" }}>
              <div className="row gap-2" style={{ alignItems: "center", marginBottom: 8 }}>
                <span className="tt-up" style={{ color: "var(--amber)", fontSize: 10, fontWeight: 600 }}>CONSENSUS · 4 of 7 personas</span>
                <div style={{ flex: 1 }} />
                <Bar value={S.confidence} label="CONFIDENCE" width={100} color="var(--amber)" showVal />
              </div>
              <p className="t-serif" style={{ fontSize: 18, color: "var(--ink-0)", lineHeight: 1.55, margin: 0, fontWeight: 400 }}>
                {S.consensus}
              </p>
              <div className="row gap-2" style={{ marginTop: 14 }}>
                {S.consensusFrom.map(id => {
                  const p = pById(id);
                  return <Chip key={id} style={{ borderColor: p.colorVar, color: p.colorVar }}>{p.initials} {p.name.split(" ").slice(-1)}</Chip>;
                })}
              </div>
            </div>

            {/* Dissent */}
            <Panel id="D" title="Dissent" sub={`${S.dissent.length} dissenting positions`}>
              <div className="col">
                {S.dissent.map((d, i) => {
                  const p = pById(d.from);
                  return (
                    <div key={i} style={{ padding: 16, borderBottom: "1px solid var(--line-1)", display: "flex", gap: 12, alignItems: "flex-start" }}>
                      <PersonaAvatar p={p} size={32} />
                      <div style={{ flex: 1 }}>
                        <div className="row gap-2" style={{ alignItems: "baseline" }}>
                          <span style={{ color: p.colorVar, fontWeight: 600, fontSize: 12 }}>{p.name}</span>
                          <span className="muted" style={{ fontSize: 10 }}>· {p.role}</span>
                        </div>
                        <p className="t-serif" style={{ fontSize: 14, color: "var(--ink-1)", margin: "6px 0 0", lineHeight: 1.5 }}>{d.point}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>

            {/* Minority report */}
            <Panel id="M" title="Minority Report" sub="single-source, high-leverage">
              <div style={{ padding: 16 }}>
                <p className="t-serif" style={{ fontSize: 14, color: "var(--ink-1)", margin: 0, lineHeight: 1.55, fontStyle: "italic" }}>
                  "{S.minority}"
                </p>
              </div>
            </Panel>

            {/* Evidence trail */}
            <Panel id="E" title="Evidence Trail" sub={`${S.evidence} citations · 9 sources · 14 KG nodes`}>
              <div style={{ padding: 16, fontSize: 11, lineHeight: 1.7 }}>
                <div className="t-mono" style={{ color: "var(--ink-1)" }}>
                  <div><span className="amber">claim 01</span> "Joint Sword 2026-A concluded 78 hours ago" → <span className="green">GDELT/PLA-EX-2026-04</span> → <span className="cyan">kg.event(ja-sword)</span></div>
                  <div><span className="amber">claim 02</span> "2005 Anti-Secession Law authorizes non-peaceful means" → <span className="green">Xinhua/Anti-Secession Law Art.8</span> → <span className="cyan">kg.doc(asl)</span></div>
                  <div><span className="amber">claim 03</span> "ROCS Hai Kun commissioned 2026-03-11" → <span className="green">Reuters/Hai Kun</span> → <span className="cyan">kg.asset(haikun)</span></div>
                  <div><span className="amber">claim 04</span> "INDOPACOM munitions flow within 96h" → <span className="green">DoD/Indo-Pacific Strategy 2025</span></div>
                  <div><span className="amber">claim 05</span> "TSMC Arizona N4P at ~20% TW capacity" → <span className="green">TSMC IR Q1 2026</span> → <span className="cyan">kg.asset(fab21)</span></div>
                  <div><span className="amber">claim 06</span> "2022 NSS reinterpretation" → <span className="green">MOFA-JP/NSS 2022</span> → <span className="cyan">kg.doc(nss22)</span></div>
                  <div><span className="amber">claim 07</span> "ESC-TW April 2026 poll: 72% status quo" → <span className="green">ESC-TW/n=1247</span></div>
                  <div className="muted">... 10 more claims, fully cited ...</div>
                </div>
              </div>
            </Panel>

            {/* Open questions */}
            <Panel id="O" title="Open Questions" sub="unresolved · synthesizer-flagged">
              <div style={{ padding: 8 }}>
                {S.open.map((q, i) => (
                  <div key={i} style={{ padding: "10px 12px", borderBottom: i < S.open.length - 1 ? "1px solid var(--line-1)" : "none", display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <span className="tab amber" style={{ fontSize: 10 }}>Q{String(i+1).padStart(2,"0")}</span>
                    <span style={{ flex: 1, fontSize: 12, color: "var(--ink-1)", lineHeight: 1.5 }}>{q}</span>
                    <Btn ghost style={{ fontSize: 9 }}>↺ RE-RUN</Btn>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          {/* SIDE COLUMN */}
          <div className="col gap-4">
            <Panel id="P" title="Probability">
              <div style={{ padding: 16 }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>QUARANTINE · 12mo</div>
                <div className="tab" style={{ fontSize: 42, color: "var(--amber)", fontWeight: 600, lineHeight: 1, margin: "4px 0" }}>0.42</div>
                <div className="row gap-2" style={{ alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: 10 }}>±0.13</span>
                  <Sparkline data={[0.18,0.22,0.28,0.31,0.35,0.39,0.42]} width={120} height={20} fill />
                </div>
                <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--line-1)" }}>
                  {[
                    { lbl: "Quarantine", p: 0.42, color: "var(--amber)" },
                    { lbl: "Blockade", p: 0.18, color: "var(--red)" },
                    { lbl: "Kinetic", p: 0.07, color: "var(--red)" },
                    { lbl: "Status quo", p: 0.33, color: "var(--green)" },
                  ].map(r => (
                    <div key={r.lbl} className="row gap-2" style={{ alignItems: "center", padding: "3px 0" }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 80 }}>{r.lbl}</span>
                      <Bar value={r.p} max={1} width={120} color={r.color} />
                      <span className="tab" style={{ fontSize: 10, color: "var(--ink-1)" }}>{r.p.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>

            <Panel id="X" title="Counterfactuals">
              <div style={{ padding: 12 }}>
                {S.counterfactuals.map((c, i) => (
                  <div key={i} style={{ padding: "8px 0", borderBottom: i < S.counterfactuals.length-1 ? "1px solid var(--line-1)" : "none" }}>
                    <div style={{ fontSize: 11, color: "var(--ink-0)", fontWeight: 500 }}>{c.name}</div>
                    <div style={{ fontSize: 10, color: "var(--ink-2)", marginTop: 2 }}>{c.impact}</div>
                  </div>
                ))}
                <Btn ghost style={{ marginTop: 8, width: "100%" }}>+ TEST COUNTERFACTUAL</Btn>
              </div>
            </Panel>

            <Panel id="A" title="Anchored to">
              <div style={{ padding: 12 }}>
                <KV k="WorldView pin" v="e1 · TW Strait" />
                <KV k="KG entity" v="tw / cn / pla" />
                <KV k="Time anchor" v="2026-04-25 14:22Z" />
                <KV k="Source" v="GDELT · PLA-EX-2026-04" />
              </div>
            </Panel>

            <Panel id="L" title="Lineage">
              <div style={{ padding: 12, fontSize: 10, color: "var(--ink-1)" }}>
                <div>↳ d-2026-04-15-03 (TW preparedness)</div>
                <div>↳ d-2026-03-22-01 (PLA exercise patterns)</div>
                <div>↳ d-2026-02-08-02 (TWD/USD scenarios)</div>
                <Btn ghost style={{ marginTop: 8 }}>↗ DIFF WITH PARENT</Btn>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// SYNTHESIS LIBRARY
// ─────────────────────────────────────────────
function LibraryScreen({ setRoute }) {
  const D = window.ARGUS_DATA;
  const [q, setQ] = us3("");
  const items = [
    ...D.RECENT,
    { id: "d-2026-04-19-04", title: "Meta-EU AI Act: §50 enforcement first-mover", time: "6d", personas: 5, status: "done" },
    { id: "d-2026-04-18-01", title: "Brazil rate cut: BCB orthodoxy under fiscal stress", time: "7d", personas: 4, status: "done" },
    { id: "d-2026-04-17-02", title: "Iran-Israel: shadow war calibration", time: "8d", personas: 6, status: "done" },
    { id: "d-2026-04-15-03", title: "Taiwan preparedness: civil-defense reforms", time: "10d", personas: 5, status: "done" },
    { id: "d-2026-04-12-04", title: "ECB September: cut vs. hold", time: "13d", personas: 4, status: "done" },
    { id: "d-2026-04-10-01", title: "Ukraine peace deal: territorial freeze scenarios", time: "15d", personas: 6, status: "done" },
  ];
  const filtered = q ? items.filter(i => i.title.toLowerCase().includes(q.toLowerCase())) : items;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="08·LIBRARY" title="Synthesis Library"
        breadcrumb={`// ${items.length} archived · 14 collections`}
        right={<div className="row gap-2">
          <Btn ghost>+ COLLECTION</Btn>
          <Btn ghost>↗ BULK EXPORT</Btn>
          <Btn ghost>◫ DIFF TWO</Btn>
        </div>}
      />
      <div className="row grow" style={{ overflow: "hidden" }}>
        <div style={{ width: 220, borderRight: "1px solid var(--line-2)", background: "var(--bg-1)", padding: 14, overflowY: "auto" }}>
          <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 6 }}>COLLECTIONS</div>
          {[
            { n: "All debates", c: items.length, sel: true },
            { n: "★ Starred", c: 4 },
            { n: "Indo-Pacific", c: 12 },
            { n: "Macro", c: 8 },
            { n: "AI policy", c: 5 },
            { n: "Climate", c: 3 },
            { n: "Recurring", c: 2 },
          ].map((c, i) => (
            <div key={i} style={{ padding: "5px 8px", display: "flex", fontSize: 11, color: c.sel ? "var(--amber)" : "var(--ink-1)", background: c.sel ? "var(--bg-3)" : "transparent", cursor: "pointer", borderLeft: c.sel ? "2px solid var(--amber)" : "2px solid transparent" }}>
              <span style={{ flex: 1 }}>{c.n}</span>
              <span className="tab muted">{c.c}</span>
            </div>
          ))}
          <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", margin: "16px 0 6px" }}>FILTERS</div>
          <div className="col gap-1" style={{ fontSize: 10 }}>
            <div>· By topic</div>
            <div>· By persona</div>
            <div>· By date range</div>
            <div>· By region</div>
            <div>· By confidence</div>
          </div>
        </div>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div style={{ padding: 12, borderBottom: "1px solid var(--line-2)", background: "var(--bg-1)" }}>
            <input value={q} onChange={e => setQ(e.target.value)} className="input" placeholder="search debates · regex supported" />
          </div>
          <div className="grow" style={{ overflowY: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 24 }}></th>
                  <th>Title</th>
                  <th style={{ width: 80 }}>ID</th>
                  <th style={{ width: 70 }}>Personas</th>
                  <th style={{ width: 90 }}>Confidence</th>
                  <th style={{ width: 70 }}>Status</th>
                  <th style={{ width: 60 }}>Age</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(d => (
                  <tr key={d.id} onClick={() => setRoute(d.status === "running" ? "debate" : "synthesis")} style={{ cursor: "pointer" }}>
                    <td>{Math.random() > 0.7 ? "★" : ""}</td>
                    <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                    <td className="tab muted">{d.id}</td>
                    <td className="tab">{d.personas}</td>
                    <td><Bar value={0.5 + Math.random()*0.4} width={70} color="var(--amber)" /></td>
                    <td><span className="tt-up" style={{ fontSize: 9, color: d.status === "running" ? "var(--amber)" : "var(--green)" }}>{d.status}</span></td>
                    <td className="tab muted">{d.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// REPLAY & BRANCH
// ─────────────────────────────────────────────
function ReplayScreen() {
  const D = window.ARGUS_DATA;
  const [scrub, setScrub] = us3(8);
  const T = D.TRANSCRIPT;
  const branches = [
    { id: "main", label: "main", color: "var(--amber)", events: [0, 2, 4, 6, 8, 10, 12], current: true },
    { id: "b1", label: "branch · inject TSMC fire", color: "var(--p-2)", events: [4, 6, 8] },
    { id: "b2", label: "branch · swap Lai → Hou Yu-ih", color: "var(--p-4)", events: [2, 4, 6, 8] },
    { id: "b3", label: "branch · add EU persona", color: "var(--p-3)", events: [6, 8, 10, 11] },
  ];

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="09·REPLAY" title="Replay & Branch"
        breadcrumb={`// d-2026-04-25-01 · scrubbing turn ${scrub}/${T.length} · ${branches.length} branches`}
        right={<div className="row gap-2">
          <Btn ghost>+ INJECT FACT</Btn>
          <Btn ghost>↻ SWAP PERSONA</Btn>
          <Btn ghost>⊕ NEW BRANCH</Btn>
          <Btn primary>SAVE BRANCH</Btn>
        </div>}
      />

      <div className="grow row" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden" }}>
          {/* Branch tree */}
          <div style={{ padding: 16, borderBottom: "1px solid var(--line-2)" }}>
            <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}>BRANCH TREE</div>
            <svg viewBox="0 0 1000 180" style={{ width: "100%", height: 180 }}>
              {branches.map((b, bi) => {
                const y = 24 + bi * 40;
                return (
                  <g key={b.id}>
                    <line x1={40} y1={y} x2={960} y2={y} stroke="var(--line-1)" strokeDasharray="2 4" />
                    <text x={20} y={y+3} fontSize="9" fill={b.color} fontFamily="JetBrains Mono">{b.label}</text>
                    {b.events.map((eIdx, i) => {
                      const x = 60 + eIdx * 70;
                      const isScrub = b.current && eIdx === scrub - 1;
                      return (
                        <g key={i}>
                          <circle cx={x} cy={y} r={isScrub ? 7 : 4} fill={b.color} stroke="var(--bg-1)" strokeWidth="2" />
                          {isScrub && <circle cx={x} cy={y} r={11} fill="none" stroke={b.color} strokeWidth="1" opacity="0.5" />}
                        </g>
                      );
                    })}
                    {/* fork lines */}
                    {bi > 0 && b.events.length > 0 && (
                      <line x1={60 + b.events[0] * 70} y1={24} x2={60 + b.events[0] * 70} y2={y - 5}
                        stroke={b.color} strokeWidth="1" />
                    )}
                  </g>
                );
              })}
              <text x={500} y={172} fontSize="9" fill="var(--ink-3)" fontFamily="JetBrains Mono" textAnchor="middle">turn 0 ─── 13 (synth)</text>
            </svg>
          </div>

          {/* Side-by-side diff */}
          <div className="grow row" style={{ overflow: "hidden" }}>
            <div className="grow col" style={{ borderRight: "1px solid var(--line-2)" }}>
              <SectionHeader id="ORIG" title="main" sub={`turn ${scrub}`} />
              <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
                {T.slice(Math.max(0, scrub-2), scrub).map((m, i) => {
                  const p = D.PERSONAS.find(pp => pp.id === m.persona);
                  return (
                    <div key={i} style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--line-1)" }}>
                      <div className="row gap-2" style={{ alignItems: "center", marginBottom: 4 }}>
                        <PersonaAvatar p={p} size={20} />
                        <span style={{ color: p.colorVar, fontSize: 11, fontWeight: 600 }}>{p.name}</span>
                        <span className="muted tt-up" style={{ fontSize: 9 }}>R{m.roundN}·{m.round}</span>
                      </div>
                      <p style={{ fontSize: 11, color: "var(--ink-1)", margin: 0, lineHeight: 1.5 }}>{m.text}</p>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="grow col">
              <SectionHeader id="BRANCH" title="branch · inject TSMC fire" sub={`turn ${scrub} · diverged at turn 4`} />
              <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
                <div style={{ padding: 10, marginBottom: 14, borderLeft: "2px solid var(--green)", background: "var(--green-glow)" }}>
                  <div className="tt-up" style={{ fontSize: 9, color: "var(--green)" }}>+ FACT INJECTED at turn 4</div>
                  <div style={{ fontSize: 11, color: "var(--ink-0)", marginTop: 4 }}>"Hsinchu Fab 18 fire reported, 6h estimated downtime, lithography section affected"</div>
                </div>
                <div style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--line-1)" }}>
                  <div className="row gap-2" style={{ alignItems: "center", marginBottom: 4 }}>
                    <PersonaAvatar p={D.PERSONAS[3]} size={20} />
                    <span style={{ color: D.PERSONAS[3].colorVar, fontSize: 11, fontWeight: 600 }}>C.C. Wei</span>
                    <Chip tone="green">DIVERGENT</Chip>
                  </div>
                  <p style={{ fontSize: 11, color: "var(--ink-1)", margin: 0, lineHeight: 1.5 }}>This changes my prior calculation. A localized Fab 18 incident, even 6h, intersects with the geopolitical timeline in ways markets cannot price... <span style={{ color: "var(--green)" }}>[divergent reasoning continues]</span></p>
                </div>
              </div>
            </div>
          </div>

          {/* Scrubber */}
          <div style={{ padding: "10px 16px", borderTop: "1px solid var(--line-2)", display: "flex", gap: 12, alignItems: "center", background: "var(--bg-1)" }}>
            <Btn ghost>◀</Btn>
            <Btn ghost>▶</Btn>
            <span className="muted tt-up" style={{ fontSize: 9 }}>turn 0</span>
            <input type="range" min={0} max={T.length} value={scrub} onChange={e => setScrub(+e.target.value)} style={{ flex: 1, accentColor: "var(--amber)" }} />
            <span className="muted tt-up" style={{ fontSize: 9 }}>{T.length}</span>
            <span className="tab amber">turn {scrub}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// COMPARE MODE
// ─────────────────────────────────────────────
function CompareScreen() {
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="10·COMPARE" title="Compare Mode"
        breadcrumb="// 2 debates · TW Strait Apr-25 vs TW Strait Mar-22"
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        {[
          { title: "Apr 25, 2026", quar: 0.42, blo: 0.18, kin: 0.07, status: "current", color: "var(--amber)" },
          { title: "Mar 22, 2026", quar: 0.31, blo: 0.14, kin: 0.05, status: "month ago", color: "var(--p-2)" },
        ].map((d, i) => (
          <div key={i} className="grow col" style={{ borderRight: i === 0 ? "1px solid var(--line-2)" : "none", padding: 24 }}>
            <div className="row gap-3" style={{ alignItems: "baseline" }}>
              <div style={{ fontSize: 22, fontWeight: 600, color: d.color }}>{d.title}</div>
              <Chip tone="amber">{d.status}</Chip>
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-1)", marginTop: 4, lineHeight: 1.5 }}>Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?</div>

            <div style={{ marginTop: 24, padding: 18, border: "1px solid var(--line-2)" }}>
              <div className="tt-up muted" style={{ fontSize: 9 }}>QUARANTINE PROBABILITY</div>
              <div className="tab" style={{ fontSize: 48, color: d.color, fontWeight: 600 }}>{d.quar.toFixed(2)}</div>
              {i === 0 && <div style={{ fontSize: 11, color: "var(--green)" }}>+0.11 vs prior · 35% relative ↑</div>}
            </div>

            <div style={{ marginTop: 16 }}>
              <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>SCENARIO DISTRIBUTION</div>
              {[["Quarantine", d.quar],["Blockade", d.blo],["Kinetic", d.kin],["Status quo", 1 - d.quar - d.blo - d.kin]].map(([l,p]) => (
                <div key={l} className="row gap-2" style={{ alignItems: "center", padding: "4px 0" }}>
                  <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 90 }}>{l}</span>
                  <Bar value={p} max={1} width={200} color={d.color} />
                  <span className="tab" style={{ fontSize: 11, color: "var(--ink-1)" }}>{p.toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 24 }}>
              <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>NEW ENTITIES SINCE{i === 0 && " MAR-22"}</div>
              <div style={{ fontSize: 11, color: "var(--ink-1)", lineHeight: 1.7 }}>
                {i === 0 ? <>· Joint Sword 2026-A<br/>· ROCS Hai Kun<br/>· INDOPACOM Status FOXTROT</> : <span className="muted">—</span>}
              </div>
            </div>

            <div style={{ marginTop: 24 }}>
              <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>CAST DELTA</div>
              <div style={{ fontSize: 11, color: "var(--ink-1)" }}>
                {i === 0 ? <><span className="green">+ Ishiba (JP)</span> · <span className="green">+ Adm. Paparo</span></> : "5 personas"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// SOURCE MONITOR
// ─────────────────────────────────────────────
function SourcesScreen() {
  const D = window.ARGUS_DATA;
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="11·SOURCES" title="Source Monitor"
        breadcrumb={`// ${D.SOURCES.length} sources · 16 ok · 1 warn · 1 down`}
        right={<div className="row gap-2">
          <Btn ghost>+ ADD RSS</Btn>
          <Btn ghost>↗ MANUAL INGEST</Btn>
          <Btn primary>RETRY ALL</Btn>
        </div>}
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden", padding: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10, overflowY: "auto", paddingRight: 4 }}>
            {D.SOURCES.map(s => {
              const tone = s.status === "down" ? "red" : s.status === "warn" ? "amber" : "green";
              return (
                <div key={s.id} className="panel" style={{ padding: 12, borderColor: tone === "red" ? "var(--red-dim)" : tone === "amber" ? "var(--amber-dim)" : "var(--line-2)" }}>
                  <div className="row gap-2" style={{ alignItems: "center", marginBottom: 6 }}>
                    <Dot tone={tone} pulse={tone !== "green"} />
                    <span style={{ fontSize: 12, color: "var(--ink-0)", fontWeight: 600 }}>{s.name}</span>
                    <div style={{ flex: 1 }} />
                    <Chip>{s.type}</Chip>
                  </div>
                  <KV k="Status" v={s.status.toUpperCase()} vColor={tone === "red" ? "var(--red)" : tone === "amber" ? "var(--amber)" : "var(--green)"} />
                  <KV k="Latency" v={s.status === "down" ? "—" : `${s.latency}s`} />
                  <KV k="Error rate" v={s.status === "down" ? "100%" : `${(s.errorRate*100).toFixed(2)}%`} />
                  <KV k="Last update" v={`−${s.lastUpdate}`} />
                  <KV k="Quality" v={s.status === "down" ? "—" : s.quality.toFixed(2)} />
                  <KV k="Coverage" v={s.coverage} />
                  <div className="row gap-2" style={{ marginTop: 8 }}>
                    <Btn ghost style={{ flex: 1, fontSize: 9, padding: "3px 6px" }}>{s.status === "down" ? "RETRY" : "PAUSE"}</Btn>
                    <Btn ghost style={{ flex: 1, fontSize: 9, padding: "3px 6px" }}>LOGS</Btn>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div style={{ width: 320, borderLeft: "1px solid var(--line-2)", background: "var(--bg-1)", overflowY: "auto" }}>
          <Panel id="STATS" title="Aggregate" sub="all sources · 24h">
            <div style={{ padding: 14 }}>
              <div className="row gap-3">
                <div style={{ flex: 1 }}>
                  <div className="tt-up muted" style={{ fontSize: 9 }}>EVENTS / HR</div>
                  <div className="tab" style={{ fontSize: 22, color: "var(--amber)", fontWeight: 600 }}>3,418</div>
                  <Sparkline data={[1.2,1.4,1.6,1.5,1.8,2.1,2.4,2.8,3.0,3.2,3.4,3.4]} width={140} height={24} />
                </div>
              </div>
              <div style={{ marginTop: 14 }}>
                <KV k="Total ingested" v="2.41M" />
                <KV k="Geocoded" v="98.2%" vColor="var(--green)" />
                <KV k="Deduped" v="−18.4%" />
                <KV k="Avg latency p95" v="2.1s" />
              </div>
            </div>
          </Panel>
          <Panel id="MAP" title="Coverage Map">
            <div style={{ padding: 14, fontSize: 10, color: "var(--ink-1)" }}>
              <div style={{ marginBottom: 4 }}>Indo-Pacific <span className="amber">▰▰▰▰▰▰▰▰▱▱</span> 81%</div>
              <div style={{ marginBottom: 4 }}>EU/UK <span className="amber">▰▰▰▰▰▰▰▱▱▱</span> 72%</div>
              <div style={{ marginBottom: 4 }}>Americas <span className="amber">▰▰▰▰▰▰▱▱▱▱</span> 64%</div>
              <div style={{ marginBottom: 4 }}>MENA <span className="amber">▰▰▰▰▱▱▱▱▱▱</span> 41%</div>
              <div style={{ marginBottom: 4 }}>Sub-Sah Africa <span className="amber">▰▰▰▱▱▱▱▱▱▱</span> 28%</div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// OBSERVABILITY / DEV CONSOLE
// ─────────────────────────────────────────────
function ObsScreen() {
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="12·OBS" title="Observability"
        breadcrumb="// langfuse · temporal · dspy · evals"
        right={<div className="row gap-2">
          <Segmented size="sm" options={["1h","24h","7d","30d"]} value="24h" onChange={() => {}} />
          <Btn ghost>↗ LANGFUSE</Btn>
        </div>}
      />
      <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
          {[
            { lbl: "DEBATES 24H", v: "47", spark: [3,4,2,5,4,6,5,7,8,6,5,4], c: "var(--amber)" },
            { lbl: "TOK 24H", v: "1.42M", spark: [80,120,90,140,180,160,220,190,250,210,240,280], c: "var(--green)" },
            { lbl: "COST 24H", v: "$31.06", spark: [2,3,2,4,5,4,6,5,7,6,7,8], c: "var(--ink-0)" },
            { lbl: "ERR RATE", v: "0.4%", spark: [1,0.8,0.6,0.4,0.5,0.3,0.4,0.4,0.4,0.5,0.4,0.4], c: "var(--red)" },
          ].map(s => (
            <Panel key={s.lbl}>
              <div style={{ padding: 14 }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>{s.lbl}</div>
                <div className="tab" style={{ fontSize: 24, color: s.c, fontWeight: 600 }}>{s.v}</div>
                <Sparkline data={s.spark} width={"100%"} height={28} color={s.c} />
              </div>
            </Panel>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Panel id="T" title="Traces" sub="last 20 · langfuse">
            <table className="tbl">
              <thead><tr><th>Trace</th><th>Model</th><th>Tok</th><th>$</th><th>Lat</th><th>Status</th></tr></thead>
              <tbody>
                {[
                  ["d-2026-04-25-01·ORCH","opus-4.1","8.2k","$0.18","12.4s","ok"],
                  ["d-2026-04-25-01·LAI","sonnet-4.5","2.1k","$0.04","3.1s","ok"],
                  ["d-2026-04-25-01·XI","sonnet-4.5","1.8k","$0.03","2.8s","ok"],
                  ["d-2026-04-25-01·INDO","opus-4.1","3.4k","$0.07","4.2s","ok"],
                  ["d-2026-04-25-01·TSMC","sonnet-4.5","1.6k","$0.03","2.5s","ok"],
                  ["d-2026-04-25-01·KG","haiku-4.5","12k","$0.04","8.1s","ok"],
                  ["d-2026-04-24-04·SYNTH","opus-4.1","9.4k","$0.21","14.2s","ok"],
                  ["src.planet·INGEST","—","—","—","—","fail"],
                  ["d-2026-04-24-02·ORCH","opus-4.1","6.8k","$0.15","10.1s","ok"],
                ].map((r,i) => (
                  <tr key={i}>
                    <td className="tab muted">{r[0]}</td>
                    <td>{r[1]}</td>
                    <td className="tab">{r[2]}</td>
                    <td className="tab">{r[3]}</td>
                    <td className="tab">{r[4]}</td>
                    <td><span style={{ color: r[5] === "ok" ? "var(--green)" : "var(--red)" }} className="tt-up">{r[5]}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <Panel id="W" title="Workflows" sub="temporal · running">
            <div style={{ padding: 14, fontFamily: "JetBrains Mono", fontSize: 10, lineHeight: 1.7 }}>
              <div><span className="green">▸</span> deliberation_v3 · d-2026-04-25-01 · turn 13/14 · running 1m 34s</div>
              <div><span className="amber">▸</span> ingest_loop · running 14h 22m · 14k events</div>
              <div><span className="amber">▸</span> kg_writer · running 14h 22m · queue 3</div>
              <div><span className="green">✓</span> deliberation_v3 · d-2026-04-24-04 · 1m 41s</div>
              <div><span className="green">✓</span> deliberation_v3 · d-2026-04-24-02 · 2m 08s</div>
              <div><span className="red">✗</span> ingest_planet · 3 retries exceeded · 8h 42m ago</div>
              <div><span className="green">✓</span> eval_consensus_quality · 47 debates · 4m 12s</div>
            </div>
          </Panel>

          <Panel id="P" title="Prompt Diffs (DSPy)" sub="auto-tuning history">
            <div style={{ padding: 14, fontFamily: "JetBrains Mono", fontSize: 10, lineHeight: 1.7 }}>
              <div><span className="muted">2026-04-24 18:02</span> · <span className="green">+0.04</span> consensus quality · orchestrator.cast_personas · v.42</div>
              <div><span className="muted">2026-04-23 09:14</span> · <span className="green">+0.02</span> citation rate · persona.synthesize · v.31</div>
              <div><span className="muted">2026-04-22 22:48</span> · <span className="red">−0.01</span> rolled back · persona.challenge · v.18</div>
              <div><span className="muted">2026-04-21 11:30</span> · <span className="green">+0.06</span> minority capture · synthesizer · v.27</div>
            </div>
          </Panel>

          <Panel id="E" title="Evals" sub="last run · 47 debates">
            <div style={{ padding: 14 }}>
              <KV k="Consensus quality" v="0.78" vColor="var(--green)" />
              <KV k="Citation coverage" v="0.91" vColor="var(--green)" />
              <KV k="Persona drift" v="0.06" vColor="var(--green)" />
              <KV k="Synthesizer faithfulness" v="0.84" vColor="var(--green)" />
              <KV k="Hallucination rate" v="0.011" vColor="var(--green)" />
              <KV k="Adversarial hold-out" v="0.71" vColor="var(--amber)" />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// SETTINGS
// ─────────────────────────────────────────────
function SettingsScreen() {
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="·SETTINGS" title="Settings" />
      <div className="grow" style={{ overflowY: "auto", padding: 24 }}>
        <div style={{ maxWidth: 720 }}>
          <Panel id="A" title="API Keys">
            <div style={{ padding: 16 }}>
              {["ANTHROPIC_API_KEY","GDELT_TOKEN","REUTERS_KEY","BRAVE_SEARCH","X_BEARER","WEIBO_KEY"].map(k => (
                <div key={k} className="row gap-2" style={{ padding: "6px 0", borderBottom: "1px solid var(--line-1)", alignItems: "center" }}>
                  <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-1)", minWidth: 200 }}>{k}</span>
                  <span className="tab muted" style={{ fontSize: 11 }}>sk-ant-···········x4f2</span>
                  <div style={{ flex: 1 }} />
                  <Dot tone="green" />
                  <Btn ghost style={{ fontSize: 9 }}>ROTATE</Btn>
                </div>
              ))}
            </div>
          </Panel>
          <Panel id="B" title="Model Preferences" style={{ marginTop: 16 }}>
            <div style={{ padding: 16 }}>
              <KV k="Orchestrator" v="opus-4.1" />
              <KV k="Personas (default)" v="sonnet-4.5" />
              <KV k="Research" v="haiku-4.5" />
              <KV k="Synthesizer" v="opus-4.1" />
              <KV k="KG writer" v="haiku-4.5" />
              <KV k="Cost ceiling / debate" v="$2.00" />
              <KV k="Hard limit / day" v="$50.00" />
            </div>
          </Panel>
          <Panel id="C" title="Persona Templates" style={{ marginTop: 16 }}>
            <div style={{ padding: 16, fontSize: 11, color: "var(--ink-1)" }}>
              42 templates · 18 official · 24 user · 7 starred
              <div style={{ marginTop: 8 }}><Btn ghost>OPEN LIBRARY →</Btn></div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SynthesisView, LibraryScreen, ReplayScreen, CompareScreen, SourcesScreen, ObsScreen, SettingsScreen });
