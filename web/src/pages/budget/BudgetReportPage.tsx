import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useBudgetReport } from "@/hooks/reports";
import { formatToman, formatPercent } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { PERSIAN_MONTHS } from "@/lib/constants";

function GaugeChart({
  value,
  max,
  label,
}: {
  value: number;
  max: number;
  label?: string;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 150) : 0;
  const displayPct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const clampedPct = Math.min(pct, 100);

  // Color based on utilization
  const color =
    pct > 100
      ? "hsl(0, 84%, 60%)"    // red
      : pct > 80
        ? "hsl(38, 92%, 50%)"  // amber
        : "hsl(142, 71%, 45%)"; // green

  const bgColor = "hsl(var(--muted))";

  // Arc calculation for 180-degree gauge
  const radius = 70;
  const strokeWidth = 14;
  const cx = 90;
  const cy = 85;
  const startAngle = -180;
  const endAngle = 0;
  const totalAngle = endAngle - startAngle;
  const valueAngle = startAngle + (totalAngle * clampedPct) / 100;

  function polarToCartesian(angle: number) {
    const rad = (angle * Math.PI) / 180;
    return {
      x: cx + radius * Math.cos(rad),
      y: cy + radius * Math.sin(rad),
    };
  }

  function describeArc(start: number, end: number) {
    const startPt = polarToCartesian(start);
    const endPt = polarToCartesian(end);
    const largeArc = end - start > 180 ? 1 : 0;
    return `M ${startPt.x} ${startPt.y} A ${radius} ${radius} 0 ${largeArc} 1 ${endPt.x} ${endPt.y}`;
  }

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 180 110" className="w-44 h-auto">
        {/* Background arc */}
        <path
          d={describeArc(startAngle, endAngle)}
          fill="none"
          stroke={bgColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        {clampedPct > 0 && (
          <path
            d={describeArc(startAngle, valueAngle)}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
        {/* Percentage text */}
        <text
          x={cx}
          y={cy - 12}
          textAnchor="middle"
          className="fill-foreground text-2xl font-bold"
          fontSize="22"
        >
          {displayPct.toFixed(0)}%
        </text>
        {/* Label text */}
        {label && (
          <text
            x={cx}
            y={cy + 8}
            textAnchor="middle"
            className="fill-muted-foreground"
            fontSize="10"
          >
            {label}
          </text>
        )}
        {/* Min/Max labels */}
        <text x={15} y={cy + 18} textAnchor="middle" className="fill-muted-foreground" fontSize="9">
          0%
        </text>
        <text x={165} y={cy + 18} textAnchor="middle" className="fill-muted-foreground" fontSize="9">
          100%
        </text>
      </svg>
      {pct > 100 && (
        <span className="mt-1 text-xs font-medium text-red-500">
          +{(pct - 100).toFixed(0)}% over budget
        </span>
      )}
    </div>
  );
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

function ProgressBar({
  value,
  max,
  className,
}: {
  value: number;
  max: number;
  className?: string;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
      <div
        className={`h-full rounded-full transition-all ${className ?? "bg-primary"}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function VarianceIndicator({ value }: { value: number }) {
  if (value > 0) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-red-600">
        <TrendingUp className="h-3.5 w-3.5" />
        {formatToman(value)}
      </span>
    );
  }
  if (value < 0) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-green-600">
        <TrendingDown className="h-3.5 w-3.5" />
        {formatToman(Math.abs(value))}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
      <Minus className="h-3.5 w-3.5" />
      {formatToman(0)}
    </span>
  );
}

export default function BudgetReportPage() {
  const { t } = useTranslation();
  const { data: reports, isLoading } = useBudgetReport();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">{t("budget.report")}</h1>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-40" />
              </CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!reports || reports.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="space-y-6"
      >
        <h1 className="text-2xl font-bold">{t("budget.report")}</h1>
        <p className="py-12 text-center text-muted-foreground">
          {t("common.noData")}
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-2xl font-bold">{t("budget.report")}</h1>

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="space-y-6"
      >
        {reports.map((report) => (
          <motion.div key={report.period.id} variants={fadeUp}>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>
                    {PERSIAN_MONTHS[report.period.month - 1]}{" "}
                    {report.period.year}
                  </CardTitle>
                  <div className="text-sm text-muted-foreground">
                    {formatPercent(report.utilization)}{" "}
                    {t("budget.utilization")}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Gauge */}
                <div className="flex justify-center">
                  <GaugeChart
                    value={report.total_actual}
                    max={report.total_planned}
                    label={t("budget.utilization")}
                  />
                </div>

                {/* Overall Progress */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t("budget.plannedAmount")}
                    </span>
                    <span className="font-medium">
                      {formatToman(report.total_planned)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t("budget.actualAmount")}
                    </span>
                    <span className="font-medium">
                      {formatToman(report.total_actual)}
                    </span>
                  </div>
                  <ProgressBar
                    value={report.total_actual}
                    max={report.total_planned}
                    className={
                      report.utilization > 100
                        ? "bg-red-500"
                        : report.utilization > 80
                          ? "bg-yellow-500"
                          : "bg-green-500"
                    }
                  />
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t("budget.variance")}
                    </span>
                    <VarianceIndicator value={report.variance} />
                  </div>
                </div>

                {/* Per-Category Items */}
                {report.items.length > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      {report.items.map((item) => {
                        const itemUtilPct =
                          item.planned > 0
                            ? (item.actual / item.planned) * 100
                            : 0;
                        return (
                          <div key={item.category_id} className="space-y-1">
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-medium">
                                {item.category_name}
                              </span>
                              <div className="flex items-center gap-3">
                                <span className="text-muted-foreground">
                                  {formatToman(item.actual)} /{" "}
                                  {formatToman(item.planned)}
                                </span>
                                <VarianceIndicator value={item.variance} />
                              </div>
                            </div>
                            <ProgressBar
                              value={item.actual}
                              max={item.planned}
                              className={
                                itemUtilPct > 100
                                  ? "bg-red-500"
                                  : itemUtilPct > 80
                                    ? "bg-yellow-500"
                                    : "bg-green-500"
                              }
                            />
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}
