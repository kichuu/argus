import type { CSSProperties, ReactNode } from "react";
import { SectionHeader } from "./SectionHeader";

type PanelProps = {
  id?: string;
  title?: string;
  sub?: string;
  right?: ReactNode;
  children?: ReactNode;
  style?: CSSProperties;
  bodyStyle?: CSSProperties;
  className?: string;
};

export function Panel({ id, title, sub, right, children, style, bodyStyle, className = "" }: PanelProps) {
  return (
    <div className={`panel col ${className}`} style={{ minHeight: 0, minWidth: 0, ...style }}>
      {(title || id) && <SectionHeader id={id} title={title} sub={sub} right={right} />}
      <div
        className="grow"
        style={{ overflow: "hidden", display: "flex", flexDirection: "column", ...bodyStyle }}
      >
        {children}
      </div>
    </div>
  );
}
