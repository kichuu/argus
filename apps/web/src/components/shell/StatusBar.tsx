"use client";
import { usePathname } from "next/navigation";
import { Dot } from "@/components/ui/Dot";
import { useClock } from "@/hooks/useClock";
import { formatUTC } from "@/lib/format";

export function StatusBar() {
  const now = useClock(1000);
  const pathname = usePathname();
  const route = pathname === "/" ? "home" : pathname.slice(1);
  const items: { tone: "green" | "amber" | "red"; label: string }[] = [
    { tone: "green", label: "ALL SYS NOMINAL" },
    { tone: "amber", label: "1 SOURCE WARN" },
    { tone: "red", label: "PLANET LABS DOWN" },
  ];
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
      {items.map((it) => (
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
