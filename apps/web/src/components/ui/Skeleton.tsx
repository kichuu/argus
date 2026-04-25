import type { CSSProperties } from "react";

type Props = {
  rows?: number;
  rowHeight?: number;
  className?: string;
  gap?: number;
  style?: CSSProperties;
};

export function Skeleton({
  rows = 3,
  rowHeight = 14,
  gap = 8,
  className = "",
  style,
}: Props) {
  return (
    <div
      className={`col ${className}`}
      style={{ gap, padding: 12, ...style }}
      aria-busy
      aria-live="polite"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="argus-skeleton-bar"
          style={{
            height: rowHeight,
            width: i === rows - 1 ? "62%" : "100%",
          }}
        />
      ))}
    </div>
  );
}
