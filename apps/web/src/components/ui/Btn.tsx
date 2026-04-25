import type { CSSProperties, ReactNode } from "react";

type Props = {
  children: ReactNode;
  onClick?: () => void;
  primary?: boolean;
  ghost?: boolean;
  active?: boolean;
  disabled?: boolean;
  style?: CSSProperties;
  title?: string;
  type?: "button" | "submit" | "reset";
};

export function Btn({
  children,
  onClick,
  primary,
  ghost,
  active,
  disabled,
  style,
  title,
  type = "button",
}: Props) {
  const cls = primary ? "btn btn-primary" : ghost ? "btn btn-ghost" : "btn";
  return (
    <button
      type={type}
      className={cls}
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        ...style,
        ...(active
          ? { background: "var(--bg-4)", borderColor: "var(--amber)", color: "var(--amber)" }
          : {}),
        ...(disabled ? { opacity: 0.4, cursor: "not-allowed" } : {}),
      }}
    >
      {children}
    </button>
  );
}
