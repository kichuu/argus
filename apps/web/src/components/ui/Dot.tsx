type Tone = "amber" | "green" | "red" | "ink";

export function Dot({ tone = "amber", pulse = false, size = 6 }: { tone?: Tone; pulse?: boolean; size?: number }) {
  const cls = `dot dot-${tone}` + (pulse ? " pulse" : "");
  return <span className={cls} style={{ width: size, height: size }} />;
}
