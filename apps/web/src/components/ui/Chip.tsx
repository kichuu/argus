import type { CSSProperties, ReactNode } from "react";

type Tone = "default" | "amber" | "green" | "red" | "solid";

export function Chip({
  children,
  tone = "default",
  style,
  onClick,
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  style?: CSSProperties;
  onClick?: () => void;
  className?: string;
}) {
  const cls =
    tone === "amber"
      ? "chip chip-amber"
      : tone === "green"
        ? "chip chip-green"
        : tone === "red"
          ? "chip chip-red"
          : tone === "solid"
            ? "chip chip-solid"
            : "chip";
  return (
    <span className={`${cls} ${className ?? ""}`} style={style} onClick={onClick}>
      {children}
    </span>
  );
}
