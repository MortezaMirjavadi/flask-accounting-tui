import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useChecks, useClearCheck, useBounceCheck, useCancelCheck } from "@/hooks";
import { useActiveWalletFilter } from "@/hooks/useActiveWalletFilter";
import { formatToman, formatJalali } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Plus, CheckCircle2, XCircle, Ban, ChevronLeft, ChevronRight } from "lucide-react";

const PER_PAGE = 20;

export default function ChecksPage() {
  const { t } = useTranslation();
  const walletFilter = useActiveWalletFilter();
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const filters = { ...walletFilter, ...(typeFilter !== "all" ? { type: typeFilter } : {}) };
  const { data: response, isLoading } = useChecks(filters, { page, per_page: PER_PAGE });

  const checks = response?.items ?? [];
  const totalPages = response?.total_pages ?? 0;
  const total = response?.total ?? 0;

  const clearCheck = useClearCheck();
  const bounceCheck = useBounceCheck();
  const cancelCheck = useCancelCheck();

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<"clear" | "bounce" | "cancel">("clear");
  const [selectedCheckId, setSelectedCheckId] = useState<number | null>(null);

  const handleAction = (checkId: number, action: "clear" | "bounce" | "cancel") => {
    setSelectedCheckId(checkId);
    setConfirmAction(action);
    setConfirmOpen(true);
  };

  const executeAction = () => {
    if (!selectedCheckId) return;

    const mutation =
      confirmAction === "clear"
        ? clearCheck
        : confirmAction === "bounce"
          ? bounceCheck
          : cancelCheck;

    mutation.mutate(selectedCheckId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setConfirmOpen(false);
        setSelectedCheckId(null);
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  const isPending = clearCheck.isPending || bounceCheck.isPending || cancelCheck.isPending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("checks.title")}</h1>
        <Link to="/checks/new">
          <Button>
            <Plus className="me-2 h-4 w-4" />
            {t("checks.addTitle")}
          </Button>
        </Link>
      </div>

      <Tabs value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
        <TabsList>
          <TabsTrigger value="all">{t("common.all")}</TabsTrigger>
          <TabsTrigger value="issued">{t("checks.issued")}</TabsTrigger>
          <TabsTrigger value="received">{t("checks.received")}</TabsTrigger>
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
      ) : checks.length > 0 ? (
        <>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("checks.checkNumber")}</TableHead>
                    <TableHead>{t("checks.bankName")}</TableHead>
                    <TableHead>{t("common.amount")}</TableHead>
                    <TableHead>{t("checks.dueDate")}</TableHead>
                    <TableHead>{t("common.type")}</TableHead>
                    <TableHead>{t("common.status")}</TableHead>
                    <TableHead className="text-end">{t("common.actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {checks.map((check) => (
                    <TableRow key={check.id}>
                      <TableCell className="font-mono font-medium">{check.check_number}</TableCell>
                      <TableCell>{check.bank_name}</TableCell>
                      <TableCell>{formatToman(check.amount)}</TableCell>
                      <TableCell>{formatJalali(check.due_date)}</TableCell>
                      <TableCell>
                        <StatusBadge status={check.type} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={check.status} />
                      </TableCell>
                      <TableCell className="text-end">
                        {check.status === "pending" && (
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleAction(check.id, "clear")}
                              title={t("checks.clear")}
                            >
                              <CheckCircle2 className="h-4 w-4 text-success" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleAction(check.id, "bounce")}
                              title={t("checks.bounce")}
                            >
                              <XCircle className="h-4 w-4 text-warning" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleAction(check.id, "cancel")}
                              title={t("common.cancel")}
                            >
                              <Ban className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        )}
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
            <EmptyState titleKey="common.noData" descriptionKey="checks.addTitle" />
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
        onConfirm={executeAction}
        loading={isPending}
        variant={confirmAction === "cancel" ? "destructive" : "default"}
      />
    </motion.div>
  );
}
