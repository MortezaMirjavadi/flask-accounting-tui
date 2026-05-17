import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Plus, Eye, Search, X, Users } from "lucide-react";
import { useTransactions } from "@/hooks/transactions";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { useCategories } from "@/hooks/categories";
import { useSources } from "@/hooks/sources";
import { useAuth } from "@/context/auth-context";
import type { Transaction } from "@/types";
import { formatToman, formatJalali } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChevronLeft, ChevronRight } from "lucide-react";

const PER_PAGE = 20;

export default function TransactionsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const walletFilter = useActiveWalletFilter();
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [sourceId, setSourceId] = useState<string>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const filters: Record<string, string> = {};
  if (categoryId) filters.category_id = categoryId;
  if (sourceId) filters.source_id = sourceId;
  if (dateFrom) filters.date_from = dateFrom;
  if (dateTo) filters.date_to = dateTo;

  const { data: response, isLoading } = useTransactions(
    Object.keys({ ...filters, ...walletFilter }).length > 0
      ? { ...filters, ...walletFilter }
      : undefined,
    { page, per_page: PER_PAGE },
  );
  const { data: categories } = useCategories();
  const { data: sources } = useSources();

  const transactions = response?.items ?? [];
  const totalPages = response?.total_pages ?? 0;
  const total = response?.total ?? 0;

  const filtered = useMemo(() => {
    if (!search.trim()) return transactions;
    const q = search.toLowerCase();
    return transactions.filter(
      (tx: Transaction) =>
        tx.description?.toLowerCase().includes(q) ||
        tx.category_name?.toLowerCase().includes(q) ||
        tx.source_name?.toLowerCase().includes(q),
    );
  }, [transactions, search]);

  const hasFilters = categoryId || sourceId || dateFrom || dateTo;

  function resetFilters() {
    setCategoryId("");
    setSourceId("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="flex h-full min-h-0 flex-col gap-6"
    >
      <div className="flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-bold">{t("transactions.title")}</h1>
        <Button asChild>
          <Link to="/transactions/new">
            <Plus className="h-4 w-4" />
            {t("nav.addTransaction")}
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex shrink-0 flex-wrap items-end gap-3">
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t("common.search")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="ps-9"
          />
        </div>

        <Select value={categoryId} onValueChange={(v) => { setCategoryId(v); setPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder={t("transactions.category")} />
          </SelectTrigger>
          <SelectContent>
            {categories?.items?.map((cat) => (
              <SelectItem key={cat.id} value={String(cat.id)}>
                {cat.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sourceId} onValueChange={(v) => { setSourceId(v); setPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder={t("transactions.source")} />
          </SelectTrigger>
          <SelectContent>
            {sources?.items?.map((src) => (
              <SelectItem key={src.id} value={String(src.id)}>
                {src.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <JalaliDatePicker
          value={dateFrom}
          onChange={(v) => { setDateFrom(v); setPage(1); }}
          className="w-[160px]"
          placeholder={t("common.date")}
        />

        <JalaliDatePicker
          value={dateTo}
          onChange={(v) => { setDateTo(v); setPage(1); }}
          className="w-[160px]"
          placeholder={t("common.date")}
        />

        {hasFilters && (
          <Button variant="ghost" size="icon" onClick={resetFilters}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="min-h-0 flex-1 space-y-3 overflow-hidden">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="py-12 text-center text-muted-foreground">
          {t("common.noData")}
        </p>
      ) : (
        <>
          <div className="min-h-0 flex-1 overflow-hidden rounded-md border">
            <Table className="table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[110px]">{t("common.date")}</TableHead>
                  <TableHead>{t("common.description")}</TableHead>
                  <TableHead className="w-[120px]">
                    {t("transactions.category")}
                  </TableHead>
                  <TableHead className="w-[120px]">
                    {t("transactions.source")}
                  </TableHead>
                  <TableHead className="w-[130px] text-end">
                    {t("common.amount")}
                  </TableHead>
                  <TableHead className="w-12 text-end">
                    {t("common.actions")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell className="whitespace-nowrap">
                      {formatJalali(tx.date)}
                    </TableCell>
                    <TableCell className="truncate">
                      {tx.description || "-"}
                    </TableCell>
                    <TableCell>
                      {tx.category_name && (
                        <span
                          className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium ${
                            tx.category_type === "income"
                              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          }`}
                        >
                          {tx.category_name}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="truncate text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <span>{tx.source_name || "-"}</span>
                        {tx.wallet_type === "shared" && (
                          <Badge
                            variant="secondary"
                            className="h-4 px-1 text-[10px]"
                          >
                            <Users className="h-2.5 w-2.5 me-0.5" />
                            {t("wallets.shared")}
                          </Badge>
                        )}
                      </div>
                      {tx.wallet_type === "shared" &&
                        tx.creator_username &&
                        tx.creator_username !== user?.username && (
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {t("common.by")}{" "}
                            {tx.creator_display_name || tx.creator_username}
                          </p>
                        )}
                    </TableCell>
                    <TableCell className="text-end font-semibold">
                      <span
                        className={
                          tx.category_type === "income"
                            ? "text-green-600"
                            : "text-red-600"
                        }
                      >
                        {tx.category_type === "income" ? "+" : "-"}{" "}
                        {formatToman(tx.amount)}
                      </span>
                    </TableCell>
                    <TableCell className="text-end">
                      <Button variant="ghost" size="icon" asChild>
                        <Link to={`/transactions/${tx.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination Controls */}
          <div className="flex shrink-0 items-center justify-between px-2">
            <div className="text-sm text-muted-foreground">
              {total} {t("common.total")}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                {t("common.previous")}
              </Button>
              <div className="text-sm text-muted-foreground">
                {t("common.page")} {page} {t("common.of")} {totalPages}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
              >
                {t("common.next")}
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}
