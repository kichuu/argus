// argus — App shell: sidebar nav, top bar, status bar, command palette
const { useState: useStateS, useEffect: useEffectS, useRef: useRefS, useMemo: useMemoS } = React;

// ─────────────────────────────────────────────
// NAV — left sidebar
// ─────────────────────────────────────────────
const NAV_SECTIONS = [
  {
    label: "Intel",
    items: [
      { id: "home",      code: "F1",  label: "Topic Launcher" },
      { id: "world",     code: "F2",  label: "WorldView" },
      { id: "kg",        code: "F3",  label: "Knowledge Graph" },
    ],
  },
  {
    label: "Council",
    items: [
      { id: "ops",       code: "F4",  label: "Agent Ops Theater" },
      { id: "personas",  code: "F5",  label: "Persona Designer" },
      { id: "debate",    code: "F6",  label: "Debate Room" },
      { id: "synthesis", code: "F7",  label: "Synthesis View" },
    ],
  },
  {
    label: "Archive",
    items: [
      { id: "library",   code: "F8",  label: "Synthesis Library" },
      { id: "replay",    code: "F9",  label: "Replay & Branch" },
      { id: "compare",   code: "F10", label: "Compare Mode" },
    ],
  },
  {
    label: "System",
    items: [
      { id: "sources",   code: "F11", label: "Source Monitor" },
      { id: "obs",       code: "F12", label: "Observability" },
      { id: "settings",  code: "·",   label: "Settings" },
    ],
  },
];

function Sidebar({ route, setRoute, collapsed, onToggle }) {
  return (
    <div style={{
      width: collapsed ? 56 : 220,
      background: "var(--bg-1)",
      borderRight: "1px solid var(--line-2)",
      display: "flex",
      flexDirection: "column",
      flexShrink: 0,
      transition: "width 0.16s ease-out",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "14px 14px 12px",
        borderBottom: "1px solid var(--line-2)",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <div style={{
          width: 24, height: 24,
          background: "var(--amber)",
          color: "var(--bg-0)",
          fontWeight: 700,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14,
          flexShrink: 0,
        }}>◉</div>
        {!collapsed && (
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1, minWidth: 0 }}>
            <span style={{ fontWeight: 700, color: "var(--ink-0)", letterSpacing: "0.02em", fontSize: 13 }}>argus</span>
            <span className="tt-up" style={{ color: "var(--ink-3)", fontSize: 9 }}>WORLD AWARENESS v0.42</span>
          </div>
        )}
      </div>

      <div className="grow" style={{ overflowY: "auto", padding: "8px 0" }}>
        {NAV_SECTIONS.map(sec => (
          <div key={sec.label} style={{ marginBottom: 12 }}>
            {!collapsed && (
              <div className="tt-up" style={{
                color: "var(--ink-3)", fontSize: 9, padding: "4px 14px 6px",
                letterSpacing: "0.16em",
              }}>{sec.label}</div>
            )}
            {sec.items.map(it => {
              const active = route === it.id;
              return (
                <div
                  key={it.id}
                  onClick={() => setRoute(it.id)}
                  style={{
                    padding: collapsed ? "6px 0" : "5px 14px",
                    display: "flex", alignItems: "center", gap: 10,
                    cursor: "pointer",
                    color: active ? "var(--amber)" : "var(--ink-1)",
                    background: active ? "var(--bg-3)" : "transparent",
                    borderLeft: active ? "2px solid var(--amber)" : "2px solid transparent",
                    fontSize: 12,
                    justifyContent: collapsed ? "center" : "flex-start",
                  }}
                  onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "var(--bg-2)"; }}
                  onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
                  title={collapsed ? it.label : ""}
                >
                  <span style={{
                    color: active ? "var(--amber)" : "var(--ink-3)",
                    fontSize: 9, minWidth: collapsed ? "auto" : 22,
                    fontFeatureSettings: "'tnum'",
                  }}>{it.code}</span>
                  {!collapsed && <span style={{ flex: 1 }}>{it.label}</span>}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <div style={{
        padding: "8px 14px",
        borderTop: "1px solid var(--line-2)",
        display: "flex", alignItems: "center", gap: 10,
        cursor: "pointer",
        color: "var(--ink-2)",
        fontSize: 10,
      }} onClick={onToggle}>
        <span>{collapsed ? "→" : "←"}</span>
        {!collapsed && <span className="tt-up">Collapse</span>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// TOP BAR — global search, notifications, profile, theme, command
// ─────────────────────────────────────────────
function TopBar({ openCmd, theme, setTheme, notifs, setNotifs }) {
  const now = useClock(1000);
  return (
    <div style={{
      height: 40,
      background: "var(--bg-1)",
      borderBottom: "1px solid var(--line-2)",
      display: "flex", alignItems: "center",
      padding: "0 12px", gap: 12,
      flexShrink: 0,
    }}>
      {/* command bar */}
      <div
        onClick={openCmd}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "5px 10px",
          background: "var(--bg-2)",
          border: "1px solid var(--line-2)",
          minWidth: 380,
          cursor: "text",
          color: "var(--ink-3)",
          fontSize: 11,
        }}>
        <span style={{ color: "var(--amber)" }}>⌘</span>
        <span>Search entities, debates, sources, geo&hellip;</span>
        <div style={{ flex: 1 }} />
        <span style={{
          fontSize: 9, padding: "1px 5px",
          border: "1px solid var(--line-2)", color: "var(--ink-2)",
        }}>⌘K</span>
      </div>

      {/* breadcrumb / time */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 18, color: "var(--ink-2)", fontSize: 10 }} className="tt-up">
        <span>{formatDate(now)}</span>
        <span className="tab amber">{formatUTC(now)}</span>
        <span>SESSION 14h 22m</span>
      </div>

      {/* live counters */}
      <LiveCounter label="ACTIVE AGENTS" value="7" tone="green" />
      <LiveCounter label="TOK/MIN" value="14.2k" tone="amber" />
      <LiveCounter label="COST 24H" value="$31.06" tone="default" />

      {/* theme toggle */}
      <Btn ghost onClick={() => setTheme(theme === "dark" ? "light" : "dark")} title="Toggle theme">
        {theme === "dark" ? "◐" : "◑"} {theme === "dark" ? "DARK" : "LIGHT"}
      </Btn>

      {/* notifications */}
      <div onClick={() => setNotifs(!notifs)} style={{
        position: "relative", padding: "4px 8px", cursor: "pointer",
        color: "var(--ink-1)", fontSize: 14, lineHeight: 1,
      }}>
        ◔
        <span style={{
          position: "absolute", top: 2, right: 2,
          background: "var(--red)", color: "var(--bg-0)",
          fontSize: 8, padding: "0 3px", fontWeight: 700,
        }}>3</span>
      </div>

      {/* user */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "3px 8px",
        border: "1px solid var(--line-2)",
        cursor: "pointer",
      }}>
        <div style={{
          width: 18, height: 18,
          background: "var(--bg-4)",
          color: "var(--ink-0)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 10, fontWeight: 600,
        }}>AK</div>
        <span style={{ fontSize: 11 }}>analyst-04</span>
      </div>
    </div>
  );
}

function LiveCounter({ label, value, tone }) {
  const color = tone === "green" ? "var(--green)" : tone === "amber" ? "var(--amber)" : "var(--ink-0)";
  return (
    <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1, alignItems: "flex-end" }}>
      <span className="tt-up" style={{ color: "var(--ink-3)", fontSize: 8 }}>{label}</span>
      <span className="tab" style={{ color, fontSize: 12, fontWeight: 600 }}>{value}</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// STATUS BAR (bottom)
// ─────────────────────────────────────────────
function StatusBar({ route, theme }) {
  const now = useClock(1000);
  const items = [
    { tone: "green", label: "ALL SYS NOMINAL" },
    { tone: "amber", label: "1 SOURCE WARN" },
    { tone: "red",   label: "PLANET LABS DOWN" },
  ];
  return (
    <div style={{
      height: 22, background: "var(--bg-1)",
      borderTop: "1px solid var(--line-2)",
      display: "flex", alignItems: "center",
      padding: "0 10px", gap: 14, fontSize: 10,
      color: "var(--ink-2)", flexShrink: 0,
    }} className="tt-up">
      <span style={{ color: "var(--amber)", fontWeight: 600 }}>argus</span>
      <span>R/{route.toUpperCase()}</span>
      {items.map(it => (
        <span key={it.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Dot tone={it.tone} pulse={it.tone !== "green"} /> {it.label}
        </span>
      ))}
      <div style={{ flex: 1 }} />
      <span>QUOTA 41% / 100k</span>
      <span>LATENCY p95 312ms</span>
      <span>BUILD a8f3c12</span>
      <span className="tab amber">{formatUTC(now)}</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// COMMAND PALETTE (Cmd-K)
// ─────────────────────────────────────────────
function CommandPalette({ open, onClose, setRoute }) {
  const [q, setQ] = useStateS("");
  const inputRef = useRefS();
  useEffectS(() => {
    if (open && inputRef.current) inputRef.current.focus();
    if (open) setQ("");
  }, [open]);

  const allItems = useMemoS(() => {
    const navs = NAV_SECTIONS.flatMap(s => s.items.map(i => ({
      kind: "nav", id: i.id, label: i.label, code: i.code, group: s.label,
    })));
    const debates = window.ARGUS_DATA.RECENT.map(d => ({ kind: "debate", id: d.id, label: d.title, code: d.id, group: "Debates" }));
    const personas = window.ARGUS_DATA.PERSONAS.map(p => ({ kind: "persona", id: p.id, label: `${p.name} — ${p.role}`, code: p.flag, group: "Personas" }));
    const ents = window.ARGUS_DATA.KG_ENTITIES.map(e => ({ kind: "entity", id: e.id, label: e.label, code: e.type, group: "Entities" }));
    return [...navs, ...debates, ...personas, ...ents];
  }, []);

  const filtered = useMemoS(() => {
    if (!q) return allItems.slice(0, 12);
    const ql = q.toLowerCase();
    return allItems.filter(i => i.label.toLowerCase().includes(ql) || i.code.toString().toLowerCase().includes(ql)).slice(0, 14);
  }, [q, allItems]);

  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)",
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        paddingTop: 100, zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 600, background: "var(--bg-2)",
          border: "1px solid var(--line-3)",
          boxShadow: "0 24px 60px rgba(0,0,0,0.6)",
        }}>
        <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--line-2)", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: "var(--amber)", fontSize: 14 }}>⌘</span>
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Type to search — entities, debates, personas, screens"
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              color: "var(--ink-0)", fontFamily: "inherit", fontSize: 13,
            }}
            onKeyDown={e => {
              if (e.key === "Escape") onClose();
              if (e.key === "Enter" && filtered[0]) {
                if (filtered[0].kind === "nav") setRoute(filtered[0].id);
                onClose();
              }
            }}
          />
          <span className="muted tt-up" style={{ fontSize: 9 }}>ESC</span>
        </div>
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {filtered.length === 0 && (
            <div style={{ padding: 20, color: "var(--ink-3)", fontSize: 11, textAlign: "center" }}>No matches</div>
          )}
          {filtered.map((it, i) => (
            <div
              key={it.kind + it.id}
              onClick={() => { if (it.kind === "nav") setRoute(it.id); onClose(); }}
              style={{
                padding: "8px 14px", display: "flex", alignItems: "center", gap: 10,
                fontSize: 12, cursor: "pointer", borderBottom: "1px solid var(--line-1)",
                background: i === 0 ? "var(--bg-3)" : "transparent",
              }}
              onMouseEnter={e => e.currentTarget.style.background = "var(--bg-3)"}
              onMouseLeave={e => e.currentTarget.style.background = i === 0 ? "var(--bg-3)" : "transparent"}
            >
              <span className="tt-up" style={{ color: "var(--amber)", fontSize: 9, minWidth: 60 }}>{it.kind}</span>
              <span style={{ flex: 1, color: "var(--ink-0)" }}>{it.label}</span>
              <span className="muted" style={{ fontSize: 10 }}>{it.code}</span>
            </div>
          ))}
        </div>
        <div style={{ padding: "6px 14px", borderTop: "1px solid var(--line-2)", display: "flex", gap: 14, fontSize: 9, color: "var(--ink-3)" }} className="tt-up">
          <span>↵ OPEN</span><span>↑↓ NAVIGATE</span><span>ESC CLOSE</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// NOTIFICATIONS DROPDOWN
// ─────────────────────────────────────────────
function NotifsPanel({ open, onClose }) {
  if (!open) return null;
  const notifs = [
    { tone: "green", t: "00:01:32", title: "Synthesis ready", sub: "Taiwan Strait — quarantine vs blockade probability" },
    { tone: "amber", t: "00:14:08", title: "New hotspot detected", sub: "Bashi Channel — events +411% (24h)" },
    { tone: "red",   t: "00:42:22", title: "Source down", sub: "Planet Labs daily imagery — ingest failed 3×" },
    { tone: "amber", t: "01:08:00", title: "Subscribed topic update", sub: "TSMC — Arizona Fab 21 ramp Q1 disclosure" },
    { tone: "default", t: "02:14:00", title: "Debate completed", sub: "OPEC+ surprise cut — 5 personas, 1m 41s" },
  ];
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 9000 }}>
      <div onClick={e => e.stopPropagation()} style={{
        position: "absolute", top: 44, right: 56,
        width: 360, background: "var(--bg-2)",
        border: "1px solid var(--line-3)",
      }}>
        <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--line-2)", display: "flex", alignItems: "center" }}>
          <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-1)", fontWeight: 600 }}>Notifications</span>
          <div style={{ flex: 1 }} />
          <span className="muted tt-up" style={{ fontSize: 9 }}>5 new</span>
        </div>
        {notifs.map((n, i) => (
          <div key={i} style={{ padding: "10px 12px", borderBottom: "1px solid var(--line-1)", display: "flex", gap: 10, alignItems: "flex-start" }}>
            <Dot tone={n.tone === "default" ? "ink" : n.tone} pulse={n.tone === "amber"} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, color: "var(--ink-0)", fontWeight: 500 }}>{n.title}</div>
              <div style={{ fontSize: 10, color: "var(--ink-2)" }}>{n.sub}</div>
            </div>
            <span className="tab muted" style={{ fontSize: 9 }}>−{n.t}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { Sidebar, TopBar, StatusBar, CommandPalette, NotifsPanel, NAV_SECTIONS });
