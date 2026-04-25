type Option<T> = T | { value: T; label: string };

type Props<T extends string | number | boolean> = {
  options: ReadonlyArray<Option<T>>;
  value: T;
  onChange: (v: T) => void;
  size?: "sm" | "md";
};

export function Segmented<T extends string | number | boolean>({
  options,
  value,
  onChange,
  size = "md",
}: Props<T>) {
  const pad = size === "sm" ? "3px 8px" : "5px 10px";
  return (
    <div style={{ display: "inline-flex", border: "1px solid var(--line-2)" }}>
      {options.map((o, i) => {
        const v = (typeof o === "object" && o !== null && "value" in o ? o.value : o) as T;
        const lbl = typeof o === "object" && o !== null && "label" in o ? o.label : String(o);
        const active = v === value;
        return (
          <button
            type="button"
            key={String(v)}
            onClick={() => onChange(v)}
            style={{
              padding: pad,
              fontSize: 10,
              fontFamily: "inherit",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              background: active ? "var(--amber)" : "transparent",
              color: active ? "var(--bg-0)" : "var(--ink-1)",
              border: "none",
              borderLeft: i === 0 ? "none" : "1px solid var(--line-2)",
              cursor: "pointer",
              fontWeight: active ? 600 : 400,
            }}
          >
            {lbl}
          </button>
        );
      })}
    </div>
  );
}
