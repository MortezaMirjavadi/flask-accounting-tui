import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { GitBranch } from "lucide-react";
import { useBudgetPeriodsWithItems } from "@/hooks/budget";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { GaugeChart } from "@/components/shared/GaugeChart";
import { formatToman, toPersianDigits } from "@/lib/format";
import { getJalaliMonthName } from "@/lib/jalali";
import type { BudgetItem, BudgetPeriodWithItems } from "@/types";

export default function BudgetTreePage() {
  const { t } = useTranslation();
  const { data: periods, isLoading } = useBudgetPeriodsWithItems();

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  const list = periods ?? [];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <GitBranch className="h-6 w-6" />
        <h1 className="text-2xl font-bold">{t("budget.treeView")}</h1>
      </div>

      {list.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("common.noData")}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {list.map((period: BudgetPeriodWithItems) => {
            const totalPlanned =
              period.items?.reduce(
                (s: number, i: BudgetItem) => s + (Number(i.planned_amount) || 0),
                0,
              ) ?? 0;
            const totalActual =
              period.items?.reduce(
                (s: number, i: BudgetItem) => s + (i.actual_amount || 0),
                0,
              ) ?? 0;
            const overallUtil =
              totalPlanned > 0 ? (totalActual / totalPlanned) * 100 : 0;
            const monthName = getJalaliMonthName(period.month);
            return (
              <Card key={period.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">
                      {monthName} {toPersianDigits(String(period.year))}
                    </CardTitle>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-muted-foreground">
                        {t("budget.plannedAmount")}:
                      </span>
                      <span className="font-semibold">
                        {formatToman(totalPlanned)}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {!period.items || period.items.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      {t("common.noData")}
                    </p>
                  ) : (
                    <>
                      {/* Overall period gauge */}
                      <div className="mb-6 flex justify-center">
                        <GaugeChart
                          value={overallUtil}
                          size={160}
                          strokeWidth={14}
                          label={t("budget.utilization")}
                          subtitle={`${formatToman(totalActual)} / ${formatToman(totalPlanned)}`}
                        />
                      </div>

                      {/* Per-category gauges */}
                      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                        {period.items.map((item: BudgetItem) => {
                          const planned = Number(item.planned_amount) || 0;
                          const actual = item.actual_amount || 0;
                          const utilization =
                            planned > 0 ? (actual / planned) * 100 : 0;
                          return (
                            <div
                              key={item.id}
                              className="flex flex-col items-center rounded-lg border p-3"
                            >
                              <GaugeChart
                                value={utilization}
                                size={90}
                                strokeWidth={8}
                              />
                              <p className="mt-1 flex w-full items-center justify-center gap-1 truncate text-center text-xs font-medium">
                                <span className="truncate">
                                  {item.category_name}
                                </span>
                                {utilization > 100 && (
                                  <Badge variant="destructive">
                                    {t("budget.overBudget")}
                                  </Badge>
                                )}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                {formatToman(actual)} / {formatToman(planned)}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
