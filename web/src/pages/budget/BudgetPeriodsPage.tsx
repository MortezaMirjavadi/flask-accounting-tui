import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Plus, Pencil, Trash2, List } from "lucide-react";
import {
  useBudgetPeriodsWithItems,
  useDeleteBudgetPeriod,
} from "@/hooks/budget";
import { PERSIAN_MONTHS } from "@/lib/constants";
import { formatToman } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function BudgetPeriodsPage() {
  const { t } = useTranslation();
  const { data: periods, isLoading } = useBudgetPeriodsWithItems();
  const deleteMutation = useDeleteBudgetPeriod();

  const [deletingPeriodId, setDeletingPeriodId] = useState<number | null>(null);

  async function handleDelete() {
    if (deletingPeriodId === null) return;
    try {
      await deleteMutation.mutateAsync(deletingPeriodId);
      toast.success(t("common.success"));
      setDeletingPeriodId(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("budget.periods")}</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/budget/report">
              {t("budget.report")}
            </Link>
          </Button>
          <Button asChild>
            <Link to="/budget/periods/new">
              <Plus className="h-4 w-4" />
              {t("budget.addPeriod")}
            </Link>
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !periods || periods.length === 0 ? (
        <p className="py-12 text-center text-muted-foreground">
          {t("common.noData")}
        </p>
      ) : (
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {periods.map((period) => (
            <motion.div key={period.id} variants={fadeUp}>
              <Card>
                <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
                  <CardTitle className="text-lg">
                    {PERSIAN_MONTHS[period.month - 1]} {period.year}
                  </CardTitle>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      asChild
                    >
                      <Link to={`/budget/periods/${period.id}/edit`}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setDeletingPeriodId(period.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {period.items && period.items.length > 0 ? (
                    <div className="space-y-2">
                      {period.items.slice(0, 3).map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between text-sm"
                        >
                          <span className="text-muted-foreground">
                            {item.category_name || `#${item.category_id}`}
                          </span>
                          <span className="font-medium">
                            {formatToman(item.planned_amount)}
                          </span>
                        </div>
                      ))}
                      {period.items.length > 3 && (
                        <p className="text-xs text-muted-foreground">
                          +{period.items.length - 3} more
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {t("common.noData")}
                    </p>
                  )}
                  <div className="mt-3 border-t pt-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full"
                      asChild
                    >
                      <Link to={`/budget/periods/${period.id}/items`}>
                        <List className="me-1.5 h-3.5 w-3.5" />
                        {t("nav.budgetItems")}
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deletingPeriodId !== null}
        onOpenChange={() => setDeletingPeriodId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("common.areYouSure")}</DialogTitle>
            <DialogDescription>{t("common.deleteConfirm")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingPeriodId(null)}
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
