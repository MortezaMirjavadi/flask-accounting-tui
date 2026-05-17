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
  const circumference = Math.PI * radius; // semi-circle
  const clamped = Math.min(Math.max(value, 0), 100);
  const offset = circumference - (clamped / 100) * circumference;
  const color = getColor(value);
  const center = size / 2;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + strokeWidth} viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}>
        {/* Background arc */}
        <path
          d={describeArc(center, center, radius, 180, 360)}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Foreground arc */}
        <path
          d={describeArc(center, center, radius, 180, 180 + (clamped / 100) * 180)}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Percentage text */}
        <text
          x={center}
          y={center - 8}
          textAnchor="middle"
          className="fill-foreground text-xl font-bold"
          dominantBaseline="middle"
        >
          {Math.round(value)}%
        </text>
        {label && (
          <text
            x={center}
            y={center + 10}
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

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}
