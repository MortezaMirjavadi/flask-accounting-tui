interface GaugeChartProps {
  value: number; // 0-100+
  size?: number;
  strokeWidth?: number;
  label?: string;
  subtitle?: string;
}

function getColor(value: number): string {
  if (value > 100) return "#ef4444";
  if (value > 80) return "#f59e0b";
  return "#22c55e";
}

export function GaugeChart({
  value,
  size = 120,
  strokeWidth = 10,
  label,
  subtitle,
}: GaugeChartProps) {
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const clamped = Math.min(Math.max(value, 0), 100);
  const color = getColor(value);

  // Upward-opening semicircle: left → top → right
  const arcLength = Math.PI * radius;
  const progress = (clamped / 100) * arcLength;
  const arcD = `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`;

  // Text sits inside the dome, vertically centered
  const textY = cy - radius * 0.35;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + strokeWidth} viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}>
        {/* Background arc */}
        <path
          d={arcD}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Progress arc */}
        <path
          d={arcD}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${progress} ${arcLength}`}
        />
        {/* Percentage text (red when over budget) */}
        <text
          x={cx}
          y={textY}
          textAnchor="middle"
          className="fill-foreground text-xl font-bold"
          style={value > 100 ? { fill: color } : undefined}
          dominantBaseline="middle"
        >
          {Math.round(value)}%
        </text>
        {label && (
          <text
            x={cx}
            y={textY + 18}
            textAnchor="middle"
            className="fill-muted-foreground text-[10px]"
            dominantBaseline="middle"
          >
            {label}
          </text>
        )}
      </svg>
      {subtitle && (
        <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
      )}
    </div>
  );
}
