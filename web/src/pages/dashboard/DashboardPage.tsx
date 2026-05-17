import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  ArrowRight,
  Plus,
} from "lucide-react";
import { useSources } from "@/hooks/sources";
import { useTransactions } from "@/hooks/transactions";
import { useDailyReport } from "@/hooks/reports";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { formatToman, formatJalali } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

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

  const totalBalance =
    sources?.reduce((sum, s) => sum + parseInt(s.amount), 0) ?? 0;
  const monthlyIncome = dailyReport?.total_income ?? 0;
  const monthlyExpense = dailyReport?.total_expenses ?? 0;

  const isLoading = sourcesLoading || transactionsLoading || reportLoading;

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
