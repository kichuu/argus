import type { ReactNode } from "react";

type Props = {
  id?: string;
  title?: string;
  sub?: string;
  right?: ReactNode;
  children?: ReactNode;
};

export function SectionHeader({ id, title, sub, right, children }: Props) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        borderBottom: "1px solid var(--line-2)",
        padding: "6px 10px",
        gap: 8,
        fontSize: 10,
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        color: "var(--ink-2)",
        background: "var(--bg-3)",
        flexShrink: 0,
      }}
    >
      {id && <span style={{ color: "var(--amber)", fontWeight: 600 }}>{id}</span>}
      {title && <span style={{ color: "var(--ink-0)", fontWeight: 600 }}>{title}</span>}
      {sub && <span className="ink-2">{sub}</span>}
      <div style={{ flex: 1 }} />
      {right}
      {children}
    </div>
  );
}
