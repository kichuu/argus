"use client";
import { Btn } from "@/components/ui/Btn";
import { useClock } from "@/hooks/useClock";
import { formatDate, formatUTC } from "@/lib/format";
import { useThemeStore } from "@/store/theme";
import { useUIStore } from "@/store/ui";

export function TopBar() {
  const now = useClock(1000);
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggle);
  const openPalette = useUIStore((s) => s.openPalette);
  const toggleNotifs = useUIStore((s) => s.toggleNotifs);

  return (
    <div
      style={{
        height: 40,
        background: "var(--bg-1)",
        borderBottom: "1px solid var(--line-2)",
        display: "flex",
        alignItems: "center",
        padding: "0 12px",
        gap: 12,
        flexShrink: 0,
      }}
    >
      <div
        onClick={openPalette}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "5px 10px",
          background: "var(--bg-2)",
          border: "1px solid var(--line-2)",
          minWidth: 380,
          cursor: "text",
          color: "var(--ink-3)",
          fontSize: 11,
        }}
      >
        <span style={{ color: "var(--amber)" }}>⌘</span>
        <span>Search entities, debates, sources, geo&hellip;</span>
        <div style={{ flex: 1 }} />
        <span
          style={{
            fontSize: 9,
            padding: "1px 5px",
            border: "1px solid var(--line-2)",
            color: "var(--ink-2)",
          }}
        >
          ⌘K
        </span>
      </div>

      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          gap: 18,
          color: "var(--ink-2)",
          fontSize: 10,
        }}
        className="tt-up"
      >
        <span>{formatDate(now)}</span>
        <span className="tab amber">{formatUTC(now)}</span>
        <span>SESSION 14h 22m</span>
      </div>

      <LiveCounter label="ACTIVE AGENTS" value="7" tone="green" />
      <LiveCounter label="TOK/MIN" value="14.2k" tone="amber" />
      <LiveCounter label="COST 24H" value="$31.06" tone="default" />

      <Btn ghost onClick={toggleTheme} title="Toggle theme">
        {theme === "dark" ? "◐" : "◑"} {theme === "dark" ? "DARK" : "LIGHT"}
      </Btn>

      <div
        onClick={toggleNotifs}
        style={{
          position: "relative",
          padding: "4px 8px",
          cursor: "pointer",
          color: "var(--ink-1)",
          fontSize: 14,
          lineHeight: 1,
        }}
      >
        ◔
        <span
          style={{
            position: "absolute",
            top: 2,
            right: 2,
            background: "var(--red)",
            color: "var(--bg-0)",
            fontSize: 8,
            padding: "0 3px",
            fontWeight: 700,
          }}
        >
          3
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "3px 8px",
          border: "1px solid var(--line-2)",
          cursor: "pointer",
        }}
      >
        <div
          style={{
            width: 18,
            height: 18,
            background: "var(--bg-4)",
            color: "var(--ink-0)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 10,
            fontWeight: 600,
          }}
        >
          AK
        </div>
        <span style={{ fontSize: 11 }}>analyst-04</span>
      </div>
    </div>
  );
}

function LiveCounter({ label, value, tone }: { label: string; value: string; tone: "green" | "amber" | "default" }) {
  const color = tone === "green" ? "var(--green)" : tone === "amber" ? "var(--amber)" : "var(--ink-0)";
  return (
    <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1, alignItems: "flex-end" }}>
      <span className="tt-up" style={{ color: "var(--ink-3)", fontSize: 8 }}>
        {label}
      </span>
      <span className="tab" style={{ color, fontSize: 12, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
}
