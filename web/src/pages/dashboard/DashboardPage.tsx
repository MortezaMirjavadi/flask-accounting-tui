import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  ArrowRight,
  Plus,
  PieChart as PieChartIcon,
  BarChart3,
} from "lucide-react";
import { useSources } from "@/hooks/sources";
import { useTransactions } from "@/hooks/transactions";
import { useDailyReport, useReportByCategory, useReportByMonth } from "@/hooks/reports";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { formatToman, formatJalali, toSafeNumber } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { CategoryBreakdown, MonthlySummary } from "@/types";

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

const PERSIAN_MONTHS = [
  "فروردین",
  "اردیبهشت",
  "خرداد",
  "تیر",
  "مرداد",
  "شهریور",
  "مهر",
  "آبان",
  "آذر",
  "دی",
  "بهمن",
  "اسفند",
];

const stagger = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

function ChartTooltipContent({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      {label && (
        <p className="mb-1.5 text-sm font-medium text-muted-foreground">
          {label}
        </p>
      )}
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-semibold">{formatToman(entry.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const walletFilter = useActiveWalletFilter();
  const { data: sourcesResp, isLoading: sourcesLoading } = useSources();
  const sources = sourcesResp?.items;
  const { data: recentTxResp, isLoading: transactionsLoading } =
    useTransactions({ limit: "10", ...walletFilter });
  const recentTransactions = recentTxResp?.items;
  const { data: dailyReport, isLoading: reportLoading } = useDailyReport(
    undefined,
    walletFilter.wallet_id ? Number(walletFilter.wallet_id) : undefined,
  );
  const { data: categoryData, isLoading: categoryLoading } =
    useReportByCategory(walletFilter);
  const { data: monthlyData, isLoading: monthlyLoading } =
    useReportByMonth(walletFilter);

  const totalBalance =
    sources?.reduce((sum, s) => sum + Number(s.total_balance ?? 0), 0) ?? 0;
  const monthlyIncome = dailyReport?.total_income ?? 0;
  const monthlyExpense = dailyReport?.total_expenses ?? 0;

  // Process category data for pie chart (expenses only)
  const categoryPieData = (categoryData ?? [])
    .filter((c: CategoryBreakdown) => c.category_type === "cost")
    .sort((a, b) => b.total - a.total)
    .slice(0, 8)
    .map((c) => ({
      name: c.category_name,
      value: toSafeNumber(c.total),
    }));

  // Process monthly data for bar chart
  const monthlyBarData = (monthlyData ?? [])
    .slice(-6)
    .map((m: MonthlySummary) => ({
      name: PERSIAN_MONTHS[(m.month - 1) % 12] ?? `ماه ${m.month}`,
      income: toSafeNumber(m.total_income),
      expense: toSafeNumber(m.total_cost ?? m.total_expenses),
    }));

  // Process wallet balance for pie chart
  const walletPieData = (sources ?? [])
    .filter((s) => Number(s.total_balance ?? 0) > 0)
    .map((s) => ({
      name: s.name,
      value: Number(s.total_balance ?? 0),
    }));

  const isLoading =
    sourcesLoading || transactionsLoading || reportLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{t("dashboard.title")}</h1>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-40" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-48" />
          </CardHeader>
          <CardContent className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("dashboard.title")}</h1>
        <Button asChild>
          <Link to="/transactions/new">
            <div className="flex items-center">
              <Plus className="h-4 w-4" />
              {t("nav.addTransaction")}
            </div>
          </Link>
        </Button>
      </div>

      {/* Summary Cards */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="grid gap-4 md:grid-cols-3"
      >
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t("dashboard.totalBalance")}
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatToman(totalBalance)}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t("dashboard.monthlyIncome")}
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatToman(monthlyIncome)}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t("dashboard.monthlyExpense")}
              </CardTitle>
              <TrendingDown className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {formatToman(monthlyExpense)}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Charts Section */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="grid gap-4 md:grid-cols-2"
      >
        {/* Category Spending Pie Chart */}
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-semibold">
                {t("dashboard.categoryBreakdown")}
              </CardTitle>
              <PieChartIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {categoryLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : categoryPieData.length === 0 ? (
                <p className="flex h-64 items-center justify-center text-muted-foreground">
                  {t("dashboard.noData")}
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={categoryPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={95}
                      paddingAngle={3}
                      dataKey="value"
                      nameKey="name"
                    >
                      {categoryPieData.map((_, index) => (
                        <Cell
                          key={index}
                          fill={COLORS[index % COLORS.length]}
                          stroke="none"
                        />
                      ))}
                    </Pie>
                    <RechartsTooltip content={<ChartTooltipContent />} />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value: string) => (
                        <span className="text-xs text-muted-foreground">
                          {value}
                        </span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Monthly Income vs Expense Bar Chart */}
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-semibold">
                {t("dashboard.monthlyTrend")}
              </CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {monthlyLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : monthlyBarData.length === 0 ? (
                <p className="flex h-64 items-center justify-center text-muted-foreground">
                  {t("dashboard.noData")}
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={monthlyBarData} barGap={4}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="stroke-muted"
                    />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11 }}
                      className="text-muted-foreground"
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      className="text-muted-foreground"
                      tickFormatter={(v) =>
                        v >= 1000000
                          ? `${(v / 1000000).toFixed(0)}M`
                          : v >= 1000
                            ? `${(v / 1000).toFixed(0)}K`
                            : `${v}`
                      }
                    />
                    <RechartsTooltip content={<ChartTooltipContent />} />
                    <Legend
                      formatter={(value: string) => (
                        <span className="text-xs text-muted-foreground">
                          {value === "income"
                            ? t("common.income")
                            : t("common.cost")}
                        </span>
                      )}
                    />
                    <Bar
                      dataKey="income"
                      fill="#22c55e"
                      radius={[4, 4, 0, 0]}
                      name="income"
                    />
                    <Bar
                      dataKey="expense"
                      fill="#ef4444"
                      radius={[4, 4, 0, 0]}
                      name="expense"
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Wallet Balance Pie Chart */}
        <motion.div variants={fadeUp} className="md:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-semibold">
                {t("dashboard.walletDistribution")}
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {sourcesLoading ? (
                <Skeleton className="h-48 w-full" />
              ) : walletPieData.length === 0 ? (
                <p className="flex h-48 items-center justify-center text-muted-foreground">
                  {t("dashboard.noData")}
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={walletPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                      nameKey="name"
                    >
                      {walletPieData.map((_, index) => (
                        <Cell
                          key={index}
                          fill={COLORS[(index + 3) % COLORS.length]}
                          stroke="none"
                        />
                      ))}
                    </Pie>
                    <RechartsTooltip content={<ChartTooltipContent />} />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value: string) => (
                        <span className="text-xs text-muted-foreground">
                          {value}
                        </span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Recent Transactions */}
      <motion.div variants={fadeUp} initial="hidden" animate="show">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t("dashboard.recentTransactions")}</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/transactions">
                {t("common.viewAll")}
                <ArrowRight className="ms-1 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {!recentTransactions || recentTransactions.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">
                {t("dashboard.noTransactions")}
              </p>
            ) : (
              <div className="space-y-0">
                {recentTransactions.map((tx, index) => (
                  <div key={tx.id}>
                    {index > 0 && <Separator className="my-2" />}
                    <Link
                      to={`/transactions/${tx.id}`}
                      className="flex items-center justify-between rounded-md p-2 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium leading-none">
                            {tx.description || tx.category_name || "-"}
                          </p>
                          {tx.category_type && (
                            <span
                              className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium ${
                                tx.category_type === "income"
                                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                  : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                              }`}
                            >
                              {tx.category_type === "income"
                                ? t("common.income")
                                : t("common.cost")}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{formatJalali(tx.date)}</span>
                          {tx.source_name && (
                            <>
                              <span>-</span>
                              <span>{tx.source_name}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <span
                        className={`text-sm font-semibold ${
                          tx.category_type === "income"
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {tx.category_type === "income" ? "+" : "-"}{" "}
                        {formatToman(tx.amount)}
                      </span>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
