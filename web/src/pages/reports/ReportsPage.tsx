import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useDailyReport, useWeeklyReport, useMonthlyReport, useCategoryChart } from "@/hooks";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { useWalletContext } from "@/context/wallet-context";
import { formatToman, formatJalali, formatNumber, toSafeNumber } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { TrendingUp, TrendingDown, Wallet, BarChart3 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import type { CategoryBreakdown, DailyReport, MonthlySummary } from "@/types";

const COLORS = [
  "#3b82f6",
  "#ef4444",
  "#22c55e",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
  "#14b8a6",
  "#a855f7",
];

function SummaryCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`rounded-full p-2 ${color}`}>{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}



function SummaryCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8 rounded-full" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32" />
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("daily");
  const walletFilter = useActiveWalletFilter();
  const { activeWallet } = useWalletContext();
  const { data: daily, isLoading: dailyLoading } = useDailyReport(undefined, activeWallet?.id);
  const { data: weekly, isLoading: weeklyLoading } = useWeeklyReport(undefined, activeWallet?.id);
  const { data: monthly, isLoading: monthlyLoading } = useMonthlyReport(undefined, undefined, activeWallet?.id);
  const { data: categoryData, isLoading: categoryLoading } = useCategoryChart(walletFilter);

  const dailyReport: Partial<DailyReport> = daily ?? {};
  const dailyTransactions = dailyReport.transactions ?? dailyReport.last_5_transactions ?? [];
  const dailyIncome = toSafeNumber(dailyReport.income ?? dailyReport.total_income);
  const dailyCost = toSafeNumber(dailyReport.cost ?? dailyReport.total_expenses);
  const dailyBalance = toSafeNumber(dailyReport.balance ?? dailyReport.net);

  const weeklyDays = (weekly?.days ?? []).map((day: DailyReport) => ({
    ...day,
    income: toSafeNumber(day.income ?? day.total_income),
    cost: toSafeNumber(day.cost ?? day.total_expenses),
    balance: toSafeNumber(day.balance ?? day.net),
  }));
  const weeklyIncome = toSafeNumber(weekly?.total_income);
  const weeklyCost = toSafeNumber(weekly?.total_cost);
  const weeklyBalance = toSafeNumber(weekly?.balance);

  const monthlyReport: Partial<MonthlySummary> = monthly ?? {};
  const monthlySummary = monthlyReport.summary ?? monthlyReport;
  const monthlyIncome = toSafeNumber(monthlySummary?.total_income);
  const monthlyCost = toSafeNumber(monthlySummary?.total_cost ?? monthlySummary?.total_expenses);
  const monthlyBalance = toSafeNumber(monthlySummary?.balance ?? monthlySummary?.net);
  const monthlyTransactionCount = toSafeNumber(monthlyReport.transaction_count ?? monthlySummary?.transaction_count);

  const rawCategories = Array.isArray(categoryData)
    ? categoryData
    : Array.isArray(monthlyReport.category_breakdown)
      ? monthlyReport.category_breakdown
      : [];
  const categoryTotal = rawCategories.reduce((sum: number, cat: CategoryBreakdown) => sum + toSafeNumber(cat.total ?? cat.actual_amount), 0);
  const categories = rawCategories.map((cat: CategoryBreakdown) => {
    const total = toSafeNumber(cat.total ?? cat.actual_amount);
    const percentage = Number.isFinite(Number(cat.percentage ?? cat.percent_used))
      ? Number(cat.percentage ?? cat.percent_used)
      : categoryTotal > 0
        ? (total / categoryTotal) * 100
        : 0;

    return {
      ...cat,
      category_id: cat.category_id ?? 0,
      category_name: cat.category_name || t("common.unknown", { defaultValue: "Unknown" }),
      total,
      count: toSafeNumber(cat.count),
      percentage,
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("reports.title")}</h1>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="daily">{t("reports.daily")}</TabsTrigger>
          <TabsTrigger value="weekly">{t("reports.weekly")}</TabsTrigger>
          <TabsTrigger value="monthly">{t("reports.monthly")}</TabsTrigger>
          <TabsTrigger value="category">{t("reports.categoryChart")}</TabsTrigger>
        </TabsList>

        {/* Daily Tab */}
        <TabsContent value="daily" className="space-y-6">
          {dailyLoading ? (
            <div className="grid gap-4 md:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SummaryCardSkeleton key={i} />
              ))}
            </div>
          ) : daily ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <SummaryCard
                  title={t("common.income")}
                  value={formatToman(dailyIncome)}
                  icon={<TrendingUp className="h-4 w-4 text-success" />}
                  color="bg-success/10"
                />
                <SummaryCard
                  title={t("common.cost")}
                  value={formatToman(dailyCost)}
                  icon={<TrendingDown className="h-4 w-4 text-destructive" />}
                  color="bg-destructive/10"
                />
                <SummaryCard
                  title={t("common.balance")}
                  value={formatToman(dailyBalance)}
                  icon={<Wallet className="h-4 w-4 text-primary" />}
                  color="bg-primary/10"
                />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>{t("reports.daily")} - {formatJalali(daily.date)}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={[
                        { name: t("common.income"), value: dailyIncome, fill: "#22c55e" },
                        { name: t("common.cost"), value: dailyCost, fill: "#ef4444" },
                      ]}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => formatToman(value)} />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {[
                          { fill: "#22c55e" },
                          { fill: "#ef4444" },
                        ].map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {dailyTransactions.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>{t("transactions.title")}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {dailyTransactions.map((tx) => (
                        <div key={tx.id} className="flex items-center justify-between rounded-lg border p-3">
                          <div>
                            <p className="font-medium">{tx.description || tx.category_name}</p>
                            <p className="text-sm text-muted-foreground">{formatJalali(tx.date)}</p>
                          </div>
                          <span
                            className={`font-semibold ${
                              tx.category_type === "income" ? "text-success" : "text-destructive"
                            }`}
                          >
                            {tx.category_type === "income" ? "+" : "-"}
                            {formatToman(tx.amount)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : null}
        </TabsContent>

        {/* Weekly Tab */}
        <TabsContent value="weekly" className="space-y-6">
          {weeklyLoading ? (
            <div className="grid gap-4 md:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SummaryCardSkeleton key={i} />
              ))}
            </div>
          ) : weekly ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <SummaryCard
                  title={t("common.income")}
                  value={formatToman(weeklyIncome)}
                  icon={<TrendingUp className="h-4 w-4 text-success" />}
                  color="bg-success/10"
                />
                <SummaryCard
                  title={t("common.cost")}
                  value={formatToman(weeklyCost)}
                  icon={<TrendingDown className="h-4 w-4 text-destructive" />}
                  color="bg-destructive/10"
                />
                <SummaryCard
                  title={t("common.balance")}
                  value={formatToman(weeklyBalance)}
                  icon={<Wallet className="h-4 w-4 text-primary" />}
                  color="bg-primary/10"
                />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>
                    {t("reports.weekly")} ({formatJalali(weekly.start_date)} - {formatJalali(weekly.end_date)})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={weeklyDays}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" tickFormatter={(v) => formatJalali(v)} />
                      <YAxis />
                      <Tooltip
                        labelFormatter={(v) => formatJalali(v)}
                        formatter={(value: number) => formatToman(value)}
                      />
                      <Bar dataKey="income" name={t("common.income")} fill="#22c55e" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="cost" name={t("common.cost")} fill="#ef4444" radius={[4, 4, 0, 0]} />
                      <Legend />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </>
          ) : null}
        </TabsContent>

        {/* Monthly Tab */}
        <TabsContent value="monthly" className="space-y-6">
          {monthlyLoading ? (
            <div className="grid gap-4 md:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SummaryCardSkeleton key={i} />
              ))}
            </div>
          ) : monthly ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <SummaryCard
                  title={t("common.income")}
                  value={formatToman(monthlyIncome)}
                  icon={<TrendingUp className="h-4 w-4 text-success" />}
                  color="bg-success/10"
                />
                <SummaryCard
                  title={t("common.cost")}
                  value={formatToman(monthlyCost)}
                  icon={<TrendingDown className="h-4 w-4 text-destructive" />}
                  color="bg-destructive/10"
                />
                <SummaryCard
                  title={t("common.balance")}
                  value={formatToman(monthlyBalance)}
                  icon={<Wallet className="h-4 w-4 text-primary" />}
                  color="bg-primary/10"
                />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>
                    {t("reports.monthly")} - {monthly.year}/{String(monthly.month).padStart(2, "0")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">{t("common.income")}</p>
                      <p className="text-lg font-semibold text-success">{formatToman(monthlyIncome)}</p>
                      <Separator />
                      <p className="text-sm text-muted-foreground">{t("common.cost")}</p>
                      <p className="text-lg font-semibold text-destructive">{formatToman(monthlyCost)}</p>
                      <Separator />
                      <p className="text-sm text-muted-foreground">{t("common.balance")}</p>
                      <p className="text-lg font-semibold">{formatToman(monthlyBalance)}</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">{t("transactions.title")}</p>
                      <p className="text-3xl font-bold">{formatNumber(monthlyTransactionCount)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : null}
        </TabsContent>

        {/* Category Chart Tab */}
        <TabsContent value="category" className="space-y-6">
          {categoryLoading ? (
            <Card>
              <CardContent className="py-8">
                <div className="flex items-center justify-center">
                  <Skeleton className="h-[300px] w-[300px] rounded-full" />
                </div>
              </CardContent>
            </Card>
          ) : categories.length > 0 ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" />
                      {t("reports.categoryChart")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={categories}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ category_name, percentage }) =>
                            `${category_name ?? ""} (${toSafeNumber(percentage).toFixed(1)}%)`
                          }
                          outerRadius={100}
                          dataKey="total"
                          nameKey="category_name"
                        >
                          {categories.map((_, index) => (
                            <Cell key={index} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number) => formatToman(value)} />
                      </PieChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>{t("reports.byCategory")}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={categories} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="category_name" type="category" width={100} />
                        <Tooltip formatter={(value: number) => formatToman(value)} />
                        <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                          {categories.map((_, index) => (
                            <Cell key={index} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>{t("reports.byCategory")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {categories.map((cat, index) => (
                      <div key={`${cat.category_id}-${index}`} className="flex items-center justify-between rounded-lg border p-3">
                        <div className="flex items-center gap-3">
                          <div
                            className="h-3 w-3 rounded-full"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          <div>
                            <p className="font-medium">{cat.category_name}</p>
                            <p className="text-sm text-muted-foreground">
                              {cat.count} {t("transactions.title").toLowerCase()}
                            </p>
                          </div>
                        </div>
                        <div className="text-end">
                          <p className="font-semibold">{formatToman(cat.total)}</p>
                          <p className="text-sm text-muted-foreground">{toSafeNumber(cat.percentage).toFixed(1)}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-muted-foreground">{t("common.noData")}</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
