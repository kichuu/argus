// argus — Topic Launcher (home), WorldView, Knowledge Graph, smaller screens
const { useState: uS, useEffect: uE, useMemo: uM, useRef: uR } = React;

// ─────────────────────────────────────────────
// HOME / TOPIC LAUNCHER
// ─────────────────────────────────────────────
function HomeScreen({ setRoute, launchDebate }) {
  const D = window.ARGUS_DATA;
  const [prompt, setPrompt] = uS("");
  const [depth, setDepth] = uS("standard");
  const [sources, setSources] = uS({ rss: true, news: true, social: true, kg: true });
  const [autoPersonas, setAutoPersonas] = uS(true);

  const launch = (text) => {
    launchDebate(text || prompt || "Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?");
    setRoute("ops");
  };

  return (
    <div className="col grow" style={{ padding: 16, gap: 16, overflowY: "auto" }}>
      <ScreenHeader code="01·HOME" title="Topic Launcher" breadcrumb="// convene a council" />

      <div className="row gap-4" style={{ flexShrink: 0 }}>
        {/* Big prompt */}
        <Panel id="A" title="New Deliberation" sub="multi-agent · world-state grounded" style={{ flex: 2, minHeight: 300 }}>
          <div className="col grow" style={{ padding: 20, gap: 14 }}>
            <div className="tt-up" style={{ color: "var(--ink-3)", fontSize: 9 }}>Topic / question</div>
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="e.g. Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months? &#10;&#10;Personas, world state, citation strictness will be auto-cast from this prompt."
              style={{
                background: "var(--bg-1)", border: "1px solid var(--line-2)",
                color: "var(--ink-0)", padding: 14, fontFamily: "inherit",
                fontSize: 14, lineHeight: 1.5, resize: "none", outline: "none",
                minHeight: 130, width: "100%",
              }}
            />
            <div className="row gap-3" style={{ flexWrap: "wrap", alignItems: "center" }}>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>Depth</span>
                <Segmented options={[{value:"quick",label:"Quick · 3p"},{value:"standard",label:"Standard · 5p"},{value:"deep",label:"Deep · 7p"}]} value={depth} onChange={setDepth} />
              </div>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>Persona casting</span>
                <Segmented options={[{value:true,label:"Auto"},{value:false,label:"Manual"}]} value={autoPersonas} onChange={setAutoPersonas} />
              </div>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>Sources</span>
                <div className="row gap-1">
                  {[["rss","RSS"],["news","News"],["social","Social"],["kg","KG only"]].map(([k,lbl]) => (
                    <span key={k} onClick={() => setSources(s => ({...s, [k]: !s[k]}))}
                      className={sources[k] ? "chip chip-amber" : "chip"}
                      style={{ cursor: "pointer" }}>
                      {sources[k] ? "■" : "□"} {lbl}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ flex: 1 }} />
            <div className="row gap-2" style={{ alignItems: "center" }}>
              <Btn primary onClick={() => launch()}>▸ CONVENE COUNCIL</Btn>
              <Btn ghost>SCHEDULE RECURRING</Btn>
              <div style={{ flex: 1 }} />
              <span className="muted tt-up" style={{ fontSize: 9 }}>EST · ~$0.42 · ~94s · 7 personas</span>
            </div>
          </div>
        </Panel>

        {/* Trending */}
        <Panel id="B" title="Trending Questions" sub="from world-state delta · 24h" style={{ flex: 1, minHeight: 300 }}>
          <div className="col" style={{ overflowY: "auto" }}>
            {D.TRENDING.map((q, i) => (
              <div key={i} onClick={() => launch(q)}
                style={{
                  padding: "10px 12px",
                  borderBottom: "1px solid var(--line-1)",
                  cursor: "pointer", display: "flex", gap: 8, alignItems: "flex-start",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--bg-3)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <span className="tab" style={{ color: "var(--amber)", fontSize: 10, minWidth: 18 }}>{String(i+1).padStart(2,"0")}</span>
                <span style={{ flex: 1, fontSize: 11, color: "var(--ink-0)", lineHeight: 1.4 }}>{q}</span>
                <span style={{ color: "var(--green)", fontSize: 10 }}>↗</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="row gap-4" style={{ flexShrink: 0, minHeight: 240 }}>
        {/* Recent debates */}
        <Panel id="C" title="Recent Debates" sub={`${D.RECENT.length} · this session`} style={{ flex: 2 }}>
          <div className="col" style={{ overflowY: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 32 }}></th>
                  <th>Topic</th>
                  <th style={{ width: 80 }}>Personas</th>
                  <th style={{ width: 70 }}>Status</th>
                  <th style={{ width: 60 }}>Age</th>
                  <th style={{ width: 30 }}></th>
                </tr>
              </thead>
              <tbody>
                {D.RECENT.map(d => (
                  <tr key={d.id} onClick={() => setRoute(d.status === "running" ? "debate" : "synthesis")} style={{ cursor: "pointer" }}>
                    <td><Dot tone={d.status === "running" ? "amber" : "green"} pulse={d.status === "running"} /></td>
                    <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                    <td className="tab">{d.personas}</td>
                    <td><span className="tt-up" style={{ fontSize: 9, color: d.status === "running" ? "var(--amber)" : "var(--ink-2)" }}>{d.status}</span></td>
                    <td className="tab muted">{d.time}</td>
                    <td className="muted">→</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* Live ingest ticker */}
        <Panel id="D" title="Live Ingest" sub="all sources · −2 min window" style={{ flex: 1 }}
          right={<><Dot tone="green" pulse /><span className="tt-up" style={{ fontSize: 9, color: "var(--green)" }}>LIVE</span></>}>
          <div className="col" style={{ overflowY: "auto" }}>
            {D.TICKER.map((t, i) => (
              <div key={i} style={{ padding: "6px 10px", borderBottom: "1px solid var(--line-1)", fontSize: 10, lineHeight: 1.4 }}>
                <div className="row gap-2" style={{ alignItems: "baseline" }}>
                  <span className="tab muted">{t.t}</span>
                  <span className="amber tt-up" style={{ fontSize: 9 }}>{t.src}</span>
                </div>
                <div style={{ color: "var(--ink-1)", marginTop: 2 }}>{t.line}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// WORLDVIEW — equirectangular projection of events
// ─────────────────────────────────────────────
function WorldView({ setRoute, launchDebate }) {
  const D = window.ARGUS_DATA;
  const [layer, setLayer] = uS("events");
  const [time, setTime] = uS("24h");
  const [topic, setTopic] = uS("all");
  const [hover, setHover] = uS(null);
  const [sel, setSel] = uS(D.EVENTS[0]);

  // svg dims (we'll let it scale)
  const W = 1000, H = 500;
  const project = (lat, lon) => ({
    x: ((lon + 180) / 360) * W,
    y: ((90 - lat) / 180) * H,
  });

  const filtered = topic === "all" ? D.EVENTS : D.EVENTS.filter(e => e.topic === topic);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="02·WORLD" title="WorldView"
        breadcrumb="// 24h · all topics · 24 events"
        right={<div className="row gap-2">
          <Segmented options={[{value:"events",label:"Events"},{value:"heat",label:"Heat"},{value:"flow",label:"Flow"}]} value={layer} onChange={setLayer} />
          <Segmented options={["24h","7d","30d"]} value={time} onChange={setTime} />
          <Btn ghost>◐ 3D / 2D</Btn>
          <Btn ghost>↗ SHARE</Btn>
        </div>}
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        {/* Map */}
        <div className="grow col grid-bg" style={{ position: "relative", overflow: "hidden", background: "var(--bg-1)" }}>
          {/* Filter chips */}
          <div style={{ position: "absolute", top: 12, left: 12, zIndex: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["all","TW Strait","Markets","Defense","Diplomatic","Supply Chain","SCS"].map(t => (
              <span key={t} onClick={() => setTopic(t)}
                className={topic === t ? "chip chip-amber" : "chip"}
                style={{ cursor: "pointer" }}>{t}</span>
            ))}
          </div>

          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%", display: "block" }} preserveAspectRatio="xMidYMid meet">
            {/* graticule */}
            {Array.from({ length: 13 }).map((_, i) => (
              <line key={"g"+i} x1={i * (W/12)} y1={0} x2={i * (W/12)} y2={H} stroke="var(--line-1)" strokeWidth="0.5" />
            ))}
            {Array.from({ length: 7 }).map((_, i) => (
              <line key={"h"+i} x1={0} y1={i * (H/6)} x2={W} y2={i * (H/6)} stroke="var(--line-1)" strokeWidth="0.5" />
            ))}
            {/* equator */}
            <line x1={0} y1={H/2} x2={W} y2={H/2} stroke="var(--line-2)" strokeWidth="1" strokeDasharray="4 4" />

            {/* Continent silhouettes — simplified polygons */}
            <g fill="var(--bg-3)" stroke="var(--line-2)" strokeWidth="0.6">
              {/* North America */}
              <path d="M 100,140 L 180,110 L 240,130 L 280,180 L 250,240 L 220,260 L 180,280 L 140,260 L 110,200 Z" />
              {/* South America */}
              <path d="M 240,300 L 280,290 L 300,340 L 295,400 L 270,440 L 250,420 L 240,360 Z" />
              {/* Europe */}
              <path d="M 470,140 L 520,130 L 540,160 L 530,190 L 490,200 L 470,180 Z" />
              {/* Africa */}
              <path d="M 480,220 L 540,210 L 570,260 L 580,330 L 540,380 L 510,380 L 490,320 L 480,260 Z" />
              {/* Asia */}
              <path d="M 540,130 L 720,120 L 800,160 L 820,200 L 790,240 L 720,260 L 660,250 L 600,230 L 560,200 L 540,170 Z" />
              {/* SEA / Indo */}
              <path d="M 720,260 L 800,270 L 820,300 L 780,310 L 740,300 Z" />
              {/* Australia */}
              <path d="M 790,330 L 870,330 L 880,370 L 830,390 L 790,370 Z" />
              {/* Greenland */}
              <path d="M 380,80 L 430,70 L 440,110 L 410,130 L 380,110 Z" />
              {/* Antarctica strip */}
              <path d="M 0,470 L 1000,470 L 1000,500 L 0,500 Z" />
              {/* Japan */}
              <path d="M 800,200 L 820,195 L 825,220 L 810,225 Z" />
              {/* UK */}
              <path d="M 460,150 L 470,148 L 472,168 L 462,170 Z" />
            </g>

            {/* Heat (radial gradients on hotspots) */}
            {layer === "heat" && filtered.map(e => {
              const p = project(e.lat, e.lon);
              return (
                <circle key={"hh"+e.id} cx={p.x} cy={p.y} r={e.severity * 60}
                  fill="var(--amber)" opacity={e.severity * 0.18}
                />
              );
            })}

            {/* Flow arcs — connect TW to other capitals */}
            {layer === "flow" && (() => {
              const tw = D.EVENTS.find(e => e.id === "e1");
              const tp = project(tw.lat, tw.lon);
              return D.EVENTS.filter(e => e.id !== "e1" && e.severity > 0.5).map(e => {
                const ep = project(e.lat, e.lon);
                const mx = (tp.x + ep.x) / 2;
                const my = Math.min(tp.y, ep.y) - 60;
                return (
                  <path key={"arc"+e.id}
                    d={`M ${tp.x} ${tp.y} Q ${mx} ${my} ${ep.x} ${ep.y}`}
                    stroke="var(--amber)" strokeWidth="1" fill="none"
                    strokeDasharray="3 3" opacity="0.5"
                  />
                );
              });
            })()}

            {/* Events */}
            {filtered.map(e => {
              const p = project(e.lat, e.lon);
              const isSel = sel?.id === e.id;
              const isHover = hover?.id === e.id;
              const r = 3 + e.severity * 6;
              const color = e.severity > 0.75 ? "var(--red)" : e.severity > 0.5 ? "var(--amber)" : "var(--ink-1)";
              return (
                <g key={e.id} style={{ cursor: "pointer" }}
                   onClick={() => setSel(e)}
                   onMouseEnter={() => setHover(e)}
                   onMouseLeave={() => setHover(null)}>
                  {(isSel || isHover) && (
                    <circle cx={p.x} cy={p.y} r={r * 2.5} fill={color} opacity="0.18" />
                  )}
                  <circle cx={p.x} cy={p.y} r={r} fill={color} opacity="0.9" />
                  <circle cx={p.x} cy={p.y} r={r + 2} fill="none" stroke={color} strokeWidth="0.6" opacity="0.6">
                    <animate attributeName="r" from={r} to={r + 8} dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite" />
                  </circle>
                  {(isSel || isHover) && (
                    <g>
                      <line x1={p.x} y1={p.y} x2={p.x + 14} y2={p.y - 14} stroke={color} strokeWidth="0.8" />
                      <text x={p.x + 16} y={p.y - 14} fill="var(--ink-0)" fontSize="9" fontFamily="JetBrains Mono">{e.label}</text>
                      <text x={p.x + 16} y={p.y - 4} fill="var(--ink-3)" fontSize="8" fontFamily="JetBrains Mono">{e.country} · {e.topic}</text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Crosshair (top-left coords readout) */}
            <text x={10} y={18} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">EQUIRECTANGULAR · WGS84 · ZOOM 1.0</text>
          </svg>

          {/* corner overlays */}
          <div style={{ position: "absolute", bottom: 12, left: 12, display: "flex", gap: 12, alignItems: "center", background: "var(--bg-2)", padding: "6px 10px", border: "1px solid var(--line-2)" }}>
            <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>Severity</span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Dot tone="red" /> <span style={{ fontSize: 10 }}>≥75</span></span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Dot tone="amber" /> <span style={{ fontSize: 10 }}>50–74</span></span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Dot tone="ink" /> <span style={{ fontSize: 10 }}>&lt;50</span></span>
          </div>
        </div>

        {/* Side rail */}
        <div className="col" style={{ width: 320, borderLeft: "1px solid var(--line-2)", background: "var(--bg-1)", overflowY: "auto" }}>
          {/* Selected pin detail */}
          {sel && (
            <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
              <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>SELECTED · {sel.country} · {sel.id.toUpperCase()}</div>
              <div style={{ fontSize: 14, color: "var(--ink-0)", marginTop: 4, fontWeight: 500, lineHeight: 1.3 }}>{sel.label}</div>
              <div className="row gap-2" style={{ marginTop: 8 }}>
                <Chip tone="amber">{sel.topic}</Chip>
                <Chip>SEV {(sel.severity*100).toFixed(0)}</Chip>
              </div>
              <div style={{ marginTop: 10 }}>
                <KV k="Lat / Lon" v={`${sel.lat.toFixed(2)}° / ${sel.lon.toFixed(2)}°`} />
                <KV k="First seen" v="−42m" />
                <KV k="Sources" v="14" />
                <KV k="Goldstein tone" v="−7.2" vColor="var(--red)" />
              </div>
              <div className="col gap-2" style={{ marginTop: 12 }}>
                <Btn primary onClick={() => { launchDebate(`What happens next at ${sel.label}?`); setRoute("ops"); }}>▸ DEBATE THIS PIN</Btn>
                <div className="row gap-2">
                  <Btn ghost>+ BOOKMARK</Btn>
                  <Btn ghost>↗ KG</Btn>
                </div>
              </div>
            </div>
          )}

          {/* Hotspots */}
          <Panel id="H" title="Hotspots" sub="ranked · 24h" style={{ flex: 1, border: "none", borderTop: "1px solid var(--line-2)" }}>
            <div className="col">
              {D.HOTSPOTS.map(h => (
                <div key={h.rank} style={{ padding: "8px 12px", borderBottom: "1px solid var(--line-1)", display: "flex", gap: 8, alignItems: "center" }}>
                  <span className="tab amber" style={{ fontSize: 11, minWidth: 16 }}>{String(h.rank).padStart(2,"0")}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, color: "var(--ink-0)" }}>{h.label}</div>
                    <div style={{ fontSize: 10, color: "var(--ink-2)" }}>{h.events24h.toLocaleString()} events</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="tab" style={{ fontSize: 10, color: h.delta.startsWith("+") ? "var(--green)" : "var(--red)" }}>{h.delta}</div>
                    <Bar value={h.severity} width={50} color="var(--amber)" />
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      {/* Time-lapse scrubber */}
      <div style={{
        height: 36, borderTop: "1px solid var(--line-2)", background: "var(--bg-1)",
        display: "flex", alignItems: "center", padding: "0 12px", gap: 12, flexShrink: 0,
      }}>
        <Btn ghost>◀</Btn>
        <Btn ghost>▶</Btn>
        <span className="muted tt-up" style={{ fontSize: 9 }}>−24h</span>
        <div style={{ flex: 1, position: "relative", height: 4, background: "var(--bg-3)" }}>
          <div style={{ width: "73%", height: "100%", background: "var(--amber)" }} />
          <div style={{ position: "absolute", left: "73%", top: -4, width: 2, height: 12, background: "var(--ink-0)" }} />
        </div>
        <span className="muted tt-up" style={{ fontSize: 9 }}>NOW</span>
        <span className="tab amber" style={{ fontSize: 10 }}>14:22:08Z</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// KNOWLEDGE GRAPH EXPLORER
// ─────────────────────────────────────────────
function KGScreen() {
  const D = window.ARGUS_DATA;
  const [sel, setSel] = uS(D.KG_ENTITIES.find(e => e.id === "tw"));
  const [filter, setFilter] = uS("all");

  const W = 800, H = 600;
  const ents = filter === "all" ? D.KG_ENTITIES : D.KG_ENTITIES.filter(e => e.type === filter);
  const entIds = new Set(ents.map(e => e.id));
  const edges = D.KG_EDGES.filter(([a,b]) => entIds.has(a) && entIds.has(b));

  const typeColor = {
    country: "var(--p-1)", person: "var(--p-2)", company: "var(--p-4)",
    org: "var(--p-3)", event: "var(--p-5)", doc: "var(--p-6)",
    asset: "var(--p-7)", place: "var(--ink-1)",
  };

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="03·KG" title="Knowledge Graph Explorer"
        breadcrumb={`// ${D.KG_ENTITIES.length} entities · ${D.KG_EDGES.length} edges · v.t = 14:22:08Z`}
        right={<div className="row gap-2">
          <Segmented size="sm" options={["all","country","person","org","company","event","place","doc","asset"]} value={filter} onChange={setFilter} />
          <Btn ghost>◐ EMBEDDINGS</Btn>
          <Btn ghost>↗ EXPORT</Btn>
        </div>}
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        {/* Graph canvas */}
        <div className="grow grid-bg" style={{ position: "relative", overflow: "hidden", background: "var(--bg-1)" }}>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%" }} preserveAspectRatio="xMidYMid meet">
            {/* Edges */}
            {edges.map(([a,b,rel], i) => {
              const ea = D.KG_ENTITIES.find(e => e.id === a);
              const eb = D.KG_ENTITIES.find(e => e.id === b);
              if (!ea || !eb) return null;
              const x1 = ea.x * W, y1 = ea.y * H, x2 = eb.x * W, y2 = eb.y * H;
              const isSel = sel && (sel.id === a || sel.id === b);
              return (
                <g key={i}>
                  <line x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke={isSel ? "var(--amber)" : "var(--line-2)"}
                    strokeWidth={isSel ? 1 : 0.5}
                    opacity={isSel ? 0.9 : 0.5}
                  />
                  {isSel && (
                    <text x={(x1+x2)/2} y={(y1+y2)/2 - 3} fontSize="8" fill="var(--amber)" fontFamily="JetBrains Mono" textAnchor="middle">{rel}</text>
                  )}
                </g>
              );
            })}
            {/* Nodes */}
            {ents.map(e => {
              const cx = e.x * W, cy = e.y * H;
              const isSel = sel?.id === e.id;
              const r = 4 + Math.sqrt(e.deg) * 1.5;
              const c = typeColor[e.type] || "var(--ink-1)";
              return (
                <g key={e.id} style={{ cursor: "pointer" }} onClick={() => setSel(e)}>
                  {isSel && <circle cx={cx} cy={cy} r={r + 8} fill={c} opacity="0.18" />}
                  <circle cx={cx} cy={cy} r={r} fill="var(--bg-1)" stroke={c} strokeWidth={isSel ? 2 : 1} />
                  <circle cx={cx} cy={cy} r={r/2} fill={c} />
                  <text x={cx + r + 5} y={cy + 3} fontSize="9" fill={isSel ? "var(--ink-0)" : "var(--ink-1)"} fontFamily="JetBrains Mono">{e.label}</text>
                </g>
              );
            })}
            <text x={10} y={18} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">FORCE-DIRECTED · t-SNE COMPONENTS · CONFIDENCE OVERLAY OFF</text>
          </svg>

          {/* legend */}
          <div style={{ position: "absolute", bottom: 12, left: 12, background: "var(--bg-2)", border: "1px solid var(--line-2)", padding: "6px 10px", display: "flex", gap: 12, fontSize: 9 }}>
            {Object.entries(typeColor).map(([k,c]) => (
              <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: c }} /> <span className="tt-up" style={{ color: "var(--ink-2)" }}>{k}</span>
              </span>
            ))}
          </div>
        </div>

        {/* details */}
        <div style={{ width: 320, borderLeft: "1px solid var(--line-2)", background: "var(--bg-1)", overflowY: "auto" }}>
          {sel && (
            <>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>{sel.type}</div>
                <div style={{ fontSize: 16, color: "var(--ink-0)", marginTop: 2, fontWeight: 600 }}>{sel.label}</div>
                <div className="row gap-2" style={{ marginTop: 8 }}>
                  <Chip tone="amber">deg {sel.deg}</Chip>
                  <Chip>conf 0.91</Chip>
                </div>
              </div>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}>HISTORY · validity windows</div>
                {[
                  { t: "2024-05-20", e: "Lai Ching-te inaugurated" },
                  { t: "2025-01-04", e: "Conscription extended to 1y" },
                  { t: "2026-03-11", e: "Hai Kun commissioned" },
                  { t: "2026-04-22", e: "Joint Sword 2026-A response" },
                ].map((h, i) => (
                  <div key={i} className="row gap-3" style={{ padding: "4px 0", fontSize: 10 }}>
                    <span className="tab muted" style={{ minWidth: 70 }}>{h.t}</span>
                    <span style={{ color: "var(--ink-1)" }}>{h.e}</span>
                  </div>
                ))}
              </div>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}>LINKED DEBATES (3)</div>
                {D.RECENT.slice(0,3).map(d => (
                  <div key={d.id} style={{ padding: "4px 0", fontSize: 11, color: "var(--ink-1)" }}>· {d.title}</div>
                ))}
              </div>
              <div style={{ padding: 14 }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}>TOP CITATIONS</div>
                <KV k="Reuters" v="412" />
                <KV k="GDELT" v="289" />
                <KV k="Xinhua" v="178" />
                <KV k="CSIS" v="44" />
              </div>
            </>
          )}
        </div>
      </div>

      {/* time scrubber */}
      <div style={{ height: 36, borderTop: "1px solid var(--line-2)", background: "var(--bg-1)", display: "flex", alignItems: "center", padding: "0 12px", gap: 12, flexShrink: 0 }}>
        <Btn ghost>◀ −1h</Btn>
        <span className="muted tt-up" style={{ fontSize: 9 }}>2024-01</span>
        <div style={{ flex: 1, height: 4, background: "var(--bg-3)" }}>
          <div style={{ width: "92%", height: "100%", background: "var(--amber)" }} />
        </div>
        <span className="muted tt-up" style={{ fontSize: 9 }}>NOW</span>
        <Btn ghost>+1h ▶</Btn>
      </div>
    </div>
  );
}

Object.assign(window, { HomeScreen, WorldView, KGScreen });
