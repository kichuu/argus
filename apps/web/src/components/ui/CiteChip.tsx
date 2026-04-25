type Props = {
  n: number;
  src: string;
  label: string;
  onClick?: () => void;
};

export function CiteChip({ n, src, label, onClick }: Props) {
  return (
    <span
      onClick={onClick}
      title={`${src}: ${label}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
        border: "1px solid var(--line-2)",
        background: "var(--bg-3)",
        padding: "0 4px",
        fontSize: 9,
        color: "var(--amber)",
        marginLeft: 3,
        cursor: onClick ? "pointer" : "default",
        verticalAlign: "baseline",
        lineHeight: 1.5,
      }}
    >
      <span style={{ color: "var(--ink-2)" }}>[{n}]</span>
      <span className="tt-up" style={{ color: "var(--ink-1)" }}>
        {src}
      </span>
    </span>
  );
}
