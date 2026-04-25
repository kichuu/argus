import type { Persona } from "@/mock/data";

export function PersonaAvatar({ p, size = 24 }: { p: Persona; size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        border: `1px solid ${p.colorVar}`,
        color: p.colorVar,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: Math.max(9, size * 0.42),
        fontWeight: 600,
        letterSpacing: "0.04em",
        flexShrink: 0,
        background: "var(--bg-2)",
      }}
    >
      {p.initials}
    </div>
  );
}
