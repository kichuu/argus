type Props = {
  data: number[];
  width?: number | string;
  height?: number;
  color?: string;
  fill?: boolean;
};

export function Sparkline({ data, width = 80, height = 18, color = "var(--amber)", fill = false }: Props) {
  if (!data || data.length === 0) return null;
  const numericW = typeof width === "number" ? width : 100;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = numericW / (data.length - 1 || 1);
  const points = data
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / range) * height).toFixed(1)}`)
    .join(" ");
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${numericW} ${height}`}
      preserveAspectRatio="none"
      style={{ display: "block" }}
    >
      {fill && (
        <polygon points={`0,${height} ${points} ${numericW},${height}`} fill={color} opacity={0.18} />
      )}
      <polyline points={points} fill="none" stroke={color} strokeWidth="1" />
    </svg>
  );
}
