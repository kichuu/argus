import type { ReactNode } from "react";

type Props = {
  code?: string;
  title: string;
  breadcrumb?: string;
  right?: ReactNode;
};

export function ScreenHeader({ code, title, breadcrumb, right }: Props) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 16px",
        borderBottom: "1px solid var(--line-2)",
        background: "var(--bg-1)",
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, minWidth: 0 }}>
        {code && (
          <span
            style={{
              color: "var(--amber)",
              fontWeight: 600,
              fontSize: 11,
              letterSpacing: "0.08em",
            }}
          >
            {code}
          </span>
        )}
        <span
          className="t-display"
          style={{ fontSize: 18, color: "var(--ink-0)", fontWeight: 600 }}
        >
          {title}
        </span>
        {breadcrumb && (
          <span className="muted" style={{ fontSize: 11 }}>
            {breadcrumb}
          </span>
        )}
      </div>
      <div style={{ flex: 1 }} />
      {right}
    </div>
  );
}
