import type { ReactNode } from "react";

export function KV({ k, v, vColor }: { k: string; v: ReactNode; vColor?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", fontSize: 11, padding: "2px 0" }}>
      <span className="tt-up" style={{ color: "var(--ink-2)", fontSize: 10 }}>
        {k}
      </span>
      <span className="dot-leader" />
      <span className="tab" style={{ color: vColor ?? "var(--ink-0)" }}>
        {v}
      </span>
    </div>
  );
}
