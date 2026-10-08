import { useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Pencil, Trash2, ArrowLeft, Users } from "lucide-react";
import {
  useTransaction,
  useTransactionItems,
  useDeleteTransaction,
} from "@/hooks/transactions";
import { useAuth } from "@/context/auth-context";
import { formatToman, formatJalali } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

export default function TransactionDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { id } = useParams<{ id: string }>();
  const txId = Number(id);

  const { data: transaction, isLoading: txLoading } = useTransaction(txId);
  const { data: items, isLoading: itemsLoading } = useTransactionItems(txId);
  const deleteMutation = useDeleteTransaction();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Permission: can the current user edit/delete this transaction?
  const canEdit = (() => {
    if (!transaction || !user) return false;
    // Personal wallet or no wallet: creator can edit
    if (!transaction.wallet_type || transaction.wallet_type === "personal") return true;
    // Shared wallet: wallet owner can edit anything
    if (transaction.wallet_owner_id === user.id) return true;
    // Shared wallet: creator can edit their own
    if (transaction.user_id === user.id) return true;
    // Otherwise: no permission
    return false;
  })();

  async function handleDelete() {
    try {
      await deleteMutation.mutateAsync(txId);
      toast.success(t("common.success"));
      navigate("/transactions");
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 403) {
        toast.error(t("wallets.noPermission"));
      } else {
        toast.error(t("common.error"));
      }
    }
  }

  if (txLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-40" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!transaction) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-muted-foreground">{t("common.noData")}</p>
        <Button variant="link" asChild className="mt-2">
          <Link to="/transactions">{t("common.back")}</Link>
        </Button>
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
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/transactions">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">
            {t("transactions.detailTitle")}
          </h1>
        </div>
        {canEdit && (
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link to={`/transactions/${txId}/edit`}>
                <Pencil className="h-4 w-4" />
                {t("common.edit")}
              </Link>
            </Button>
            <Button
              variant="destructive"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="h-4 w-4" />
              {t("common.delete")}
            </Button>
          </div>
        )}
      </div>

      {/* Transaction Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              {transaction.description || t("transactions.detailTitle")}
            </CardTitle>
            <Badge
              variant="outline"
              className={
                transaction.category_type === "income"
                  ? "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400"
                  : "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400"
              }
            >
              {transaction.category_type === "income"
                ? t("common.income")
                : t("common.cost")}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("common.amount")}
              </p>
              <p
                className={`text-2xl font-bold ${
                  transaction.category_type === "income"
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              >
                {formatToman(transaction.amount)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("common.date")}
              </p>
              <p className="text-lg font-medium">
                {formatJalali(transaction.date)}
              </p>
            </div>
          </div>

          <Separator />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("transactions.category")}
              </p>
              <p className="font-medium">
                {transaction.category_name || "-"}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("transactions.source")}
              </p>
              <div className="flex items-center gap-1.5">
                <p className="font-medium">
                  {transaction.source_name || "-"}
                </p>
                {transaction.wallet_type === "shared" && (
                  <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                    <Users className="h-3 w-3 me-0.5" />
                    {t("wallets.shared")}
                  </Badge>
                )}
              </div>
              {transaction.wallet_type === "shared" && transaction.creator_username && transaction.creator_username !== user?.username && (
                <p className="text-xs text-muted-foreground">
                  {t("common.by")} {transaction.creator_display_name || transaction.creator_username}
                </p>
              )}
            </div>
          </div>

          {transaction.description && (
            <>
              <Separator />
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  {t("common.description")}
                </p>
                <p>{transaction.description}</p>
              </div>
            </>
          )}

          {((transaction.tags && transaction.tags.length > 0) ||
            (transaction.labels && transaction.labels.length > 0)) && (
            <>
              <Separator />
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    {t("nav.tags")}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {transaction.tags?.map((tag) => (
                      <span
                        key={`tag-${tag.id}`}
                        className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary"
                        style={
                          tag.color
                            ? { backgroundColor: tag.color, color: "#fff" }
                            : undefined
                        }
                      >
                        {tag.name}
                      </span>
                    ))}
                    {!transaction.tags?.length && (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    {t("nav.labels")}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {transaction.labels?.map((label) => (
                      <span
                        key={`label-${label.id}`}
                        className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
                        style={
                          label.color
                            ? { backgroundColor: label.color, color: "#fff" }
                            : undefined
                        }
                      >
                        {label.name}
                      </span>
                    ))}
                    {!transaction.labels?.length && (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Line Items */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            {t("transactions.items")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {itemsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !items || items.length === 0 ? (
            <p className="py-6 text-center text-muted-foreground">
              {t("transactions.noItems")}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("transactions.itemName")}</TableHead>
                  <TableHead>{t("transactions.quantity")}</TableHead>
                  <TableHead>{t("transactions.unit")}</TableHead>
                  <TableHead className="text-end">
                    {t("transactions.unitPrice")}
                  </TableHead>
                  <TableHead className="text-end">
                    {t("transactions.totalPrice")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell>{item.quantity}</TableCell>
                    <TableCell>{item.unit || "-"}</TableCell>
                    <TableCell className="text-end">
                      {formatToman(item.unit_price)}
                    </TableCell>
                    <TableCell className="text-end font-medium">
                      {formatToman(item.total_price)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("common.areYouSure")}</DialogTitle>
            <DialogDescription>{t("common.deleteConfirm")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
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
