import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Plus, Eye, Search, X, ChevronLeft, ChevronRight } from "lucide-react";
import { useTransfers } from "@/hooks/transactions";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { useSources } from "@/hooks/sources";
import type { TransferListItem } from "@/types";
import { formatToman, formatJalali } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

const PER_PAGE = 20;

export default function TransfersPage() {
  const { t } = useTranslation();
  const walletFilter = useActiveWalletFilter();
  const [search, setSearch] = useState("");
  const [sourceId, setSourceId] = useState<string>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const filters: Record<string, string> = {};
  if (sourceId) filters.source_id = sourceId;
  if (dateFrom) filters.date_from = dateFrom;
  if (dateTo) filters.date_to = dateTo;

  const { data: response, isLoading } = useTransfers(
    Object.keys({ ...filters, ...walletFilter }).length > 0
      ? { ...filters, ...walletFilter }
      : undefined,
    { page, per_page: PER_PAGE },
  );
  const { data: sourcesResp } = useSources();
  const sources = sourcesResp?.items;

  const transfers = response?.items ?? [];
  const totalPages = response?.total_pages ?? 0;
  const total = response?.total ?? 0;

  const filtered = useMemo(() => {
    if (!search.trim()) return transfers;
    const q = search.toLowerCase();
    return transfers.filter(
      (tr: TransferListItem) =>
        tr.from_source_name?.toLowerCase().includes(q) ||
        tr.to_source_name?.toLowerCase().includes(q) ||
        tr.notes?.toLowerCase().includes(q),
    );
  }, [transfers, search]);

  const hasFilters = sourceId || dateFrom || dateTo;

  function resetFilters() {
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
        <h1 className="text-2xl font-bold">{t("transfers.title")}</h1>
        <Button asChild>
          <Link to="/transactions/new?transfer=true">
            <Plus className="h-4 w-4" />
            {t("nav.addTransfer")}
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

        <Select
          value={sourceId}
          onValueChange={(v) => { setSourceId(v); setPage(1); }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder={t("transactions.source")} />
          </SelectTrigger>
          <SelectContent>
            {sources?.map((src) => (
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
                  <TableHead className="w-[100px]">{t("common.date")}</TableHead>
                  <TableHead className="w-[170px]">{t("transfers.fromAccount")}</TableHead>
                  <TableHead className="w-[170px]">{t("transfers.toAccount")}</TableHead>
                  <TableHead className="w-[130px] text-end">{t("common.amount")}</TableHead>
                  <TableHead className="w-[130px]">{t("common.description")}</TableHead>
                  <TableHead className="w-12 text-end">
                    {t("common.actions")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((tr) => (
                  <TableRow key={tr.id}>
                    <TableCell className="whitespace-nowrap">
                      {formatJalali(tr.date)}
                    </TableCell>
                    <TableCell className="truncate">{tr.from_source_name}</TableCell>
                    <TableCell className="truncate">{tr.to_source_name}</TableCell>
                    <TableCell className="text-end font-semibold">
                      {formatToman(tr.amount)}
                    </TableCell>
                    <TableCell className="truncate text-muted-foreground">
                      {tr.notes || "-"}
                    </TableCell>
                    <TableCell className="text-end">
                      <Button variant="ghost" size="icon" asChild>
                        <Link to={`/transactions/${tr.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex shrink-0 items-center justify-between px-2">
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
      )}
    </motion.div>
  );
}
