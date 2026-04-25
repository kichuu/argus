"use client";
import { useQuery } from "@tanstack/react-query";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { useClock } from "@/hooks/useClock";
import { api } from "@/lib/api";
import { formatDate, formatUTC } from "@/lib/format";
import { useThemeStore } from "@/store/theme";
import { useUIStore } from "@/store/ui";

export function TopBar() {
  const now = useClock(1000);
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggle);
  const openPalette = useUIStore((s) => s.openPalette);
  const toggleNotifs = useUIStore((s) => s.toggleNotifs);

  const sysQ = useQuery({
    queryKey: ["health-system"],
    queryFn: api.systemStatus,
    refetchInterval: 10_000,
    retry: 0,
    staleTime: 10_000,
  });

  const activityQ = useQuery({
    queryKey: ["activity"],
    queryFn: () => api.activity({ limit: 20 }),
    refetchInterval: 30_000,
    retry: 0,
    staleTime: 30_000,
  });

  const sys = sysQ.data;
  const eventCount = activityQ.data?.events.length ?? 0;

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
      </div>

      <Chip tone={sys?.qdrant.available ? "green" : "amber"}>
        <Dot tone={sys?.qdrant.available ? "green" : "amber"} pulse={!sys?.qdrant.available} />
        <span style={{ marginLeft: 6 }}>
          {sys?.qdrant.available ? "qdrant ok" : "qdrant offline"}
        </span>
      </Chip>

      <Chip tone={sys?.age.available ? "green" : "amber"}>
        <Dot tone={sys?.age.available ? "green" : "amber"} pulse={!sys?.age.available} />
        <span style={{ marginLeft: 6 }}>
          {sys?.age.available ? "age ok" : "age offline"}
        </span>
      </Chip>

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
        title="Recent activity"
      >
        ◔
        {eventCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: 2,
              right: 2,
              background: "var(--amber)",
              color: "var(--bg-0)",
              fontSize: 8,
              padding: "0 3px",
              fontWeight: 700,
            }}
          >
            {eventCount > 99 ? "99+" : eventCount}
          </span>
        )}
      </div>
    </div>
  );
}
