import type { CSSProperties } from "react";
import { Btn } from "./Btn";

type Props = {
  message: string;
  onRetry?: () => void;
  className?: string;
  style?: CSSProperties;
};

export function ErrorBox({ message, onRetry, className = "", style }: Props) {
  return (
    <div
      className={`row gap-2 ${className}`}
      style={{
        alignItems: "center",
        border: "1px solid var(--red-dim)",
        background: "var(--red-glow)",
        padding: "8px 12px",
        fontSize: 11,
        color: "var(--red)",
        ...style,
      }}
    >
      <span style={{ fontWeight: 600 }}>×</span>
      <span style={{ flex: 1, color: "var(--ink-1)" }}>{message}</span>
      {onRetry && (
        <Btn ghost onClick={onRetry}>
          RETRY
        </Btn>
      )}
    </div>
  );
}
