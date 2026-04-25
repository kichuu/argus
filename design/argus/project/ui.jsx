// argus — shared UI primitives (Bloomberg-terminal aesthetic)
// Loaded after React. Exports components onto window.

const { useState, useEffect, useRef, useMemo, useCallback, createContext, useContext, Fragment } = React;

// ─────────────────────────────────────────────
// THEME / NAV CONTEXT
// ─────────────────────────────────────────────
const AppContext = createContext(null);

const useApp = () => useContext(AppContext);

// ─────────────────────────────────────────────
// CLOCK — tabular, ticking
// ─────────────────────────────────────────────
function useClock(intervalMs = 1000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

function pad(n, w = 2) { return String(n).padStart(w, "0"); }

function formatUTC(d) {
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`;
}

function formatDate(d) {
  const m = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
  return `${pad(d.getUTCDate())} ${m[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

// ─────────────────────────────────────────────
// SECTION HEADER (the panel header bar)
// ─────────────────────────────────────────────
function SectionHeader({ id, title, sub, right, children }) {
  return (
    <div style={{
      display: "flex", alignItems: "center",
      borderBottom: "1px solid var(--line-2)",
      padding: "6px 10px",
      gap: 8, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em",
      color: "var(--ink-2)",
      background: "var(--bg-3)",
      flexShrink: 0,
    }}>
      {id && <span style={{ color: "var(--amber)", fontWeight: 600 }}>{id}</span>}
      <span style={{ color: "var(--ink-0)", fontWeight: 600 }}>{title}</span>
      {sub && <span className="ink-2">{sub}</span>}
      <div style={{ flex: 1 }} />
      {right}
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────
// PANEL
// ─────────────────────────────────────────────
function Panel({ id, title, sub, right, children, style, bodyStyle, className = "" }) {
  return (
    <div className={`panel col ${className}`} style={{ minHeight: 0, minWidth: 0, ...style }}>
      {(title || id) && <SectionHeader id={id} title={title} sub={sub} right={right} />}
      <div className="grow" style={{ overflow: "hidden", display: "flex", flexDirection: "column", ...bodyStyle }}>
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// CHIP / BADGE
// ─────────────────────────────────────────────
function Chip({ children, tone = "default", style }) {
  const cls = tone === "amber" ? "chip chip-amber"
    : tone === "green" ? "chip chip-green"
    : tone === "red" ? "chip chip-red"
    : tone === "solid" ? "chip chip-solid"
    : "chip";
  return <span className={cls} style={style}>{children}</span>;
}

// ─────────────────────────────────────────────
// PERSONA AVATAR (abstract)
// ─────────────────────────────────────────────
function PersonaAvatar({ p, size = 24 }) {
  return (
    <div style={{
      width: size, height: size,
      border: `1px solid ${p.colorVar}`,
      color: p.colorVar,
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      fontSize: Math.max(9, size * 0.42),
      fontWeight: 600,
      letterSpacing: "0.04em",
      flexShrink: 0,
      background: "var(--bg-2)",
    }}>
      {p.initials}
    </div>
  );
}

// ─────────────────────────────────────────────
// SPARKLINE
// ─────────────────────────────────────────────
function Sparkline({ data, width = 80, height = 18, color = "var(--amber)", fill = false }) {
  if (!data || !data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1 || 1);
  const points = data.map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / range) * height).toFixed(1)}`).join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {fill && <polygon points={`0,${height} ${points} ${width},${height}`} fill={color} opacity={0.18} />}
      <polyline points={points} fill="none" stroke={color} strokeWidth="1" />
    </svg>
  );
}

// ─────────────────────────────────────────────
// BAR (for confidence, severity)
// ─────────────────────────────────────────────
function Bar({ value, max = 1, color = "var(--amber)", width = 80, height = 4, label, showVal = false }) {
  const pct = Math.max(0, Math.min(1, value / max));
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 10 }}>
      {label && <span className="muted tt-up" style={{ minWidth: 36 }}>{label}</span>}
      <div style={{ width, height, background: "var(--bg-4)", position: "relative" }}>
        <div style={{ width: `${pct * 100}%`, height: "100%", background: color }} />
      </div>
      {showVal && <span className="tab" style={{ color: "var(--ink-1)", minWidth: 26, textAlign: "right" }}>{(pct * 100).toFixed(0)}</span>}
    </div>
  );
}

// ─────────────────────────────────────────────
// STATUS DOT
// ─────────────────────────────────────────────
function Dot({ tone = "amber", pulse = false, size = 6 }) {
  const cls = `dot dot-${tone}` + (pulse ? " pulse" : "");
  return <span className={cls} style={{ width: size, height: size }} />;
}

// ─────────────────────────────────────────────
// KEY-VALUE LIST (with dot leader)
// ─────────────────────────────────────────────
function KV({ k, v, vColor }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", fontSize: 11, padding: "2px 0" }}>
      <span className="tt-up" style={{ color: "var(--ink-2)", fontSize: 10 }}>{k}</span>
      <span className="dot-leader" />
      <span className="tab" style={{ color: vColor || "var(--ink-0)" }}>{v}</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// BUTTON
// ─────────────────────────────────────────────
function Btn({ children, onClick, primary, ghost, active, disabled, style, title }) {
  const cls = primary ? "btn btn-primary" : ghost ? "btn btn-ghost" : "btn";
  return (
    <button
      className={cls}
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        ...style,
        ...(active ? { background: "var(--bg-4)", borderColor: "var(--amber)", color: "var(--amber)" } : {}),
        ...(disabled ? { opacity: 0.4, cursor: "not-allowed" } : {}),
      }}
    >
      {children}
    </button>
  );
}

// ─────────────────────────────────────────────
// SEGMENTED CONTROL
// ─────────────────────────────────────────────
function Segmented({ options, value, onChange, size = "md" }) {
  const pad = size === "sm" ? "3px 8px" : "5px 10px";
  return (
    <div style={{ display: "inline-flex", border: "1px solid var(--line-2)" }}>
      {options.map((o, i) => {
        const v = typeof o === "string" ? o : o.value;
        const lbl = typeof o === "string" ? o : o.label;
        const active = v === value;
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            style={{
              padding: pad, fontSize: 10, fontFamily: "inherit",
              textTransform: "uppercase", letterSpacing: "0.08em",
              background: active ? "var(--amber)" : "transparent",
              color: active ? "var(--bg-0)" : "var(--ink-1)",
              border: "none",
              borderLeft: i === 0 ? "none" : "1px solid var(--line-2)",
              cursor: "pointer",
              fontWeight: active ? 600 : 400,
            }}
          >
            {lbl}
          </button>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────
// CITATION CHIP — small numeric link
// ─────────────────────────────────────────────
function CiteChip({ n, src, label, onClick }) {
  return (
    <span
      onClick={onClick}
      title={`${src}: ${label}`}
      style={{
        display: "inline-flex", alignItems: "center", gap: 3,
        border: "1px solid var(--line-2)",
        background: "var(--bg-3)",
        padding: "0 4px",
        fontSize: 9,
        color: "var(--amber)",
        marginLeft: 3,
        cursor: "pointer",
        verticalAlign: "baseline",
        lineHeight: 1.5,
      }}
    >
      <span style={{ color: "var(--ink-2)" }}>[{n}]</span>
      <span className="tt-up" style={{ color: "var(--ink-1)" }}>{src}</span>
    </span>
  );
}

// ─────────────────────────────────────────────
// SCREEN HEADER (top of each route)
// ─────────────────────────────────────────────
function ScreenHeader({ code, title, breadcrumb, right }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12,
      padding: "10px 16px",
      borderBottom: "1px solid var(--line-2)",
      background: "var(--bg-1)",
      flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, minWidth: 0 }}>
        {code && <span style={{ color: "var(--amber)", fontWeight: 600, fontSize: 11, letterSpacing: "0.08em" }}>{code}</span>}
        <span className="t-display" style={{ fontSize: 18, color: "var(--ink-0)", fontWeight: 600 }}>{title}</span>
        {breadcrumb && <span className="muted" style={{ fontSize: 11 }}>{breadcrumb}</span>}
      </div>
      <div style={{ flex: 1 }} />
      {right}
    </div>
  );
}

// ─────────────────────────────────────────────
// ASCII spinner
// ─────────────────────────────────────────────
function AsciiSpinner({ chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"], speed = 80, color = "var(--amber)" }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI(x => (x + 1) % chars.length), speed);
    return () => clearInterval(id);
  }, [chars.length, speed]);
  return <span style={{ color }}>{chars[i]}</span>;
}

// ─────────────────────────────────────────────
// TYPEWRITER (used in Debate Room for streaming)
// ─────────────────────────────────────────────
function useTypewriter(text, enabled, speed = 8, onDone) {
  const [out, setOut] = useState(enabled ? "" : text);
  useEffect(() => {
    if (!enabled) { setOut(text); return; }
    setOut("");
    let i = 0;
    const id = setInterval(() => {
      i += Math.max(1, Math.floor(text.length / 200));
      if (i >= text.length) {
        setOut(text);
        clearInterval(id);
        onDone && onDone();
      } else {
        setOut(text.slice(0, i));
      }
    }, speed);
    return () => clearInterval(id);
  }, [text, enabled]);
  return out;
}

// ─────────────────────────────────────────────
// EXPORT to window
// ─────────────────────────────────────────────
Object.assign(window, {
  AppContext, useApp, useClock, formatUTC, formatDate, pad,
  SectionHeader, Panel, Chip, PersonaAvatar, Sparkline, Bar, Dot, KV,
  Btn, Segmented, CiteChip, ScreenHeader, AsciiSpinner, useTypewriter,
});
