"use client";
import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { Dot } from "@/components/ui/Dot";
import { useClock } from "@/hooks/useClock";
import { api } from "@/lib/api";
import { formatUTC } from "@/lib/format";

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "—";
  const diff = Math.max(0, Date.now() - then);
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function StatusBar() {
  const now = useClock(1000);
  const pathname = usePathname();
  const route = pathname === "/" ? "home" : pathname.slice(1);

  const sysQ = useQuery({
    queryKey: ["health-system"],
    queryFn: api.systemStatus,
    refetchInterval: 10_000,
    retry: 0,
    staleTime: 10_000,
  });

  const sys = sysQ.data;
  const apiOnline = sysQ.isSuccess;
  const debatesLive = sys?.db.discussions_running ?? 0;

  return (
    <div
      style={{
        height: 22,
        background: "var(--bg-1)",
        borderTop: "1px solid var(--line-2)",
        display: "flex",
        alignItems: "center",
        padding: "0 10px",
        gap: 14,
        fontSize: 10,
        color: "var(--ink-2)",
        flexShrink: 0,
      }}
      className="tt-up"
    >
      <span style={{ color: "var(--amber)", fontWeight: 600 }}>argus</span>
      <span>R/{route.toUpperCase()}</span>

      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <Dot
          tone={apiOnline ? "green" : sysQ.isLoading ? "ink" : "red"}
          pulse={!apiOnline && !sysQ.isLoading}
        />
        {apiOnline ? "API ONLINE" : sysQ.isLoading ? "API CHECKING" : "API DOWN"}
      </span>

      {sys && (
        <>
          <span>SCHEDULER {sys.scheduler.running ? "ON" : "OFF"}</span>
          <span>
            INGEST {relativeTime(sys.last_ingest_at)}
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Dot tone={debatesLive > 0 ? "amber" : "ink"} pulse={debatesLive > 0} />
            {debatesLive > 0
              ? `${debatesLive} DEBATE${debatesLive === 1 ? "" : "S"} LIVE`
              : "IDLE"}
          </span>
        </>
      )}

      <div style={{ flex: 1 }} />
      {sys && (
        <span>
          v{sys.api_version}
        </span>
      )}
      <span className="tab amber">{formatUTC(now)}</span>
    </div>
  );
}
