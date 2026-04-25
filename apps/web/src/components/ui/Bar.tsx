type Props = {
  value: number;
  max?: number;
  color?: string;
  width?: number | string;
  height?: number;
  label?: string;
  showVal?: boolean;
  unit?: string;
};

export function Bar({
  value,
  max = 1,
  color = "var(--amber)",
  width = 80,
  height = 4,
  label,
  showVal = false,
  unit = "%",
}: Props) {
  const pct = Math.max(0, Math.min(1, value / max));
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 10 }}>
      {label && (
        <span className="muted tt-up" style={{ minWidth: 36 }}>
          {label}
        </span>
      )}
      <div style={{ width, height, background: "var(--bg-4)", position: "relative" }}>
        <div style={{ width: `${pct * 100}%`, height: "100%", background: color }} />
      </div>
      {showVal && (
        <span className="tab" style={{ color: "var(--ink-1)", minWidth: 32, textAlign: "right" }}>
          {(pct * 100).toFixed(0)}{unit}
        </span>
      )}
    </div>
  );
}
