import type { CSSProperties } from "react";
import { Btn } from "./Btn";

type Props = {
  title: string;
  hint?: string;
  cta?: { label: string; onClick: () => void };
  className?: string;
  style?: CSSProperties;
};

export function EmptyState({ title, hint, cta, className = "", style }: Props) {
  return (
    <div
      className={`col center ${className}`}
      style={{
        border: "1px dashed var(--line-2)",
        background: "var(--bg-1)",
        padding: 20,
        gap: 8,
        textAlign: "center",
        ...style,
      }}
    >
      <div
        className="tt-up"
        style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: "0.12em" }}
      >
        {title}
      </div>
      {hint && (
        <div style={{ fontSize: 10, color: "var(--ink-3)", lineHeight: 1.5, maxWidth: 320 }}>
          {hint}
        </div>
      )}
      {cta && (
        <div style={{ marginTop: 4 }}>
          <Btn ghost onClick={cta.onClick}>
            {cta.label}
          </Btn>
        </div>
      )}
    </div>
  );
}
