"use client";
import { Dot } from "@/components/ui/Dot";
import { useUIStore } from "@/store/ui";

type Notif = {
  tone: "green" | "amber" | "red" | "default";
  t: string;
  title: string;
  sub: string;
};

const NOTIFS: Notif[] = [
  { tone: "green", t: "00:01:32", title: "Synthesis ready", sub: "Taiwan Strait — quarantine vs blockade probability" },
  { tone: "amber", t: "00:14:08", title: "New hotspot detected", sub: "Bashi Channel — events +411% (24h)" },
  { tone: "red", t: "00:42:22", title: "Source down", sub: "Planet Labs daily imagery — ingest failed 3×" },
  { tone: "amber", t: "01:08:00", title: "Subscribed topic update", sub: "TSMC — Arizona Fab 21 ramp Q1 disclosure" },
  { tone: "default", t: "02:14:00", title: "Debate completed", sub: "OPEC+ surprise cut — 5 personas, 1m 41s" },
];

export function NotifsPanel() {
  const open = useUIStore((s) => s.notifsOpen);
  const close = useUIStore((s) => s.closeNotifs);
  if (!open) return null;
  return (
    <div onClick={close} style={{ position: "fixed", inset: 0, zIndex: 9000 }}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "absolute",
          top: 44,
          right: 56,
          width: 360,
          background: "var(--bg-2)",
          border: "1px solid var(--line-3)",
        }}
      >
        <div
          style={{
            padding: "8px 12px",
            borderBottom: "1px solid var(--line-2)",
            display: "flex",
            alignItems: "center",
          }}
        >
          <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-1)", fontWeight: 600 }}>
            Notifications
          </span>
          <div style={{ flex: 1 }} />
          <span className="muted tt-up" style={{ fontSize: 9 }}>
            5 new
          </span>
        </div>
        {NOTIFS.map((n, i) => (
          <div
            key={i}
            style={{
              padding: "10px 12px",
              borderBottom: "1px solid var(--line-1)",
              display: "flex",
              gap: 10,
              alignItems: "flex-start",
            }}
          >
            <Dot tone={n.tone === "default" ? "ink" : n.tone} pulse={n.tone === "amber"} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, color: "var(--ink-0)", fontWeight: 500 }}>{n.title}</div>
              <div style={{ fontSize: 10, color: "var(--ink-2)" }}>{n.sub}</div>
            </div>
            <span className="tab muted" style={{ fontSize: 9 }}>
              −{n.t}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
