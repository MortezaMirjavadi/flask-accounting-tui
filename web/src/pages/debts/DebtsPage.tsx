import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useDebts, useDebtSummary, useOverdueDebts, useDueSoonDebts } from "@/hooks";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { formatToman, formatJalali } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, Eye, TrendingUp, TrendingDown, Scale, AlertTriangle, Clock, ChevronLeft, ChevronRight } from "lucide-react";

const PER_PAGE = 20;

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

export default function DebtsPage() {
  const { t } = useTranslation();
  const walletFilter = useActiveWalletFilter();
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const filters = { ...walletFilter, ...(typeFilter !== "all" ? { type: typeFilter } : {}) };
  const { data: response, isLoading } = useDebts(filters, { page, per_page: PER_PAGE });
  const { data: summary, isLoading: summaryLoading } = useDebtSummary(walletFilter);
  const { data: overdueDebts } = useOverdueDebts(walletFilter);
  const { data: dueSoonDebts } = useDueSoonDebts(walletFilter);

  const debts = response?.items ?? [];
  const totalPages = response?.total_pages ?? 0;
  const total = response?.total ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("debts.title")}</h1>
        <Link to="/debts/new">
          <Button>
            <Plus className="me-2 h-4 w-4" />
            {t("debts.addTitle")}
          </Button>
        </Link>
      </div>

      {/* Summary Cards */}
      {summaryLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : summary ? (
        <div className="grid gap-4 md:grid-cols-3">
          <SummaryCard
            title={t("debts.totalPayable")}
            value={formatToman(summary.total_payable)}
            icon={<TrendingDown className="h-4 w-4 text-destructive" />}
            color="bg-destructive/10"
          />
          <SummaryCard
            title={t("debts.totalReceivable")}
            value={formatToman(summary.total_receivable)}
            icon={<TrendingUp className="h-4 w-4 text-success" />}
            color="bg-success/10"
          />
          <SummaryCard
            title={t("common.balance")}
            value={formatToman(summary.net)}
            icon={<Scale className="h-4 w-4 text-primary" />}
            color="bg-primary/10"
          />
        </div>
      ) : null}

      {/* Overdue & Due Soon Alerts */}
      {overdueDebts && overdueDebts.length > 0 && (
        <Card className="border-red-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base text-red-600">
              <AlertTriangle className="h-4 w-4" /> {t("debts.overdue")} ({overdueDebts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {overdueDebts.map((debt) => (
                <Link key={debt.id} to={`/debts/${debt.id}`} className="flex items-center justify-between rounded-md border p-2 transition-colors hover:bg-muted/50">
                  <div>
                    <p className="text-sm font-medium">{debt.title}</p>
                    <p className="text-xs text-muted-foreground">{debt.counterparty_name}</p>
                  </div>
                  <span className="font-semibold text-red-600">{formatToman(debt.remaining_amount)}</span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {dueSoonDebts && dueSoonDebts.length > 0 && (
        <Card className="border-yellow-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base text-yellow-600">
              <Clock className="h-4 w-4" /> {t("debts.dueSoon")} ({dueSoonDebts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dueSoonDebts.map((debt) => (
                <Link key={debt.id} to={`/debts/${debt.id}`} className="flex items-center justify-between rounded-md border p-2 transition-colors hover:bg-muted/50">
                  <div>
                    <p className="text-sm font-medium">{debt.title}</p>
                    <p className="text-xs text-muted-foreground">{debt.counterparty_name} · {debt.due_date ? formatJalali(debt.due_date) : ""}</p>
                  </div>
                  <span className="font-semibold text-yellow-600">{formatToman(debt.remaining_amount)}</span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
        <TabsList>
          <TabsTrigger value="all">{t("common.all")}</TabsTrigger>
          <TabsTrigger value="payable">{t("debts.payable")}</TabsTrigger>
          <TabsTrigger value="receivable">{t("debts.receivable")}</TabsTrigger>
        </TabsList>
      </Tabs>

      {isLoading ? (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                    <TableHead key={i}>
                      <Skeleton className="h-4 w-20" />
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {[1, 2, 3, 4, 5, 6, 7].map((j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : debts.length > 0 ? (
        <>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("common.name")}</TableHead>
                    <TableHead>{t("debts.counterparty")}</TableHead>
                    <TableHead>{t("debts.originalAmount")}</TableHead>
                    <TableHead>{t("debts.remainingAmount")}</TableHead>
                    <TableHead>{t("common.status")}</TableHead>
                    <TableHead>{t("checks.dueDate")}</TableHead>
                    <TableHead className="text-end">{t("common.actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {debts.map((debt) => (
                    <TableRow key={debt.id}>
                      <TableCell className="font-medium">{debt.title}</TableCell>
                      <TableCell>{debt.counterparty_name}</TableCell>
                      <TableCell>{formatToman(debt.original_amount)}</TableCell>
                      <TableCell>
                        <span className={debt.remaining_amount > 0 ? "text-destructive font-medium" : ""}>
                          {formatToman(debt.remaining_amount)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={debt.status} />
                      </TableCell>
                      <TableCell>
                        {debt.due_date ? formatJalali(debt.due_date) : "-"}
                      </TableCell>
                      <TableCell className="text-end">
                        <Link to={`/debts/${debt.id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Pagination */}
          <div className="flex items-center justify-between px-2">
            <div className="text-sm text-muted-foreground">
              {total} {t("common.total")}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page <= 1}>
                <ChevronLeft className="h-4 w-4" /> {t("common.previous")}
              </Button>
              <div className="text-sm text-muted-foreground">
                {t("common.page")} {page} {t("common.of")} {totalPages}
              </div>
              <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages}>
                {t("common.next")} <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      ) : (
        <Card>
          <CardContent>
            <EmptyState titleKey="common.noData" descriptionKey="debts.addTitle" />
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
