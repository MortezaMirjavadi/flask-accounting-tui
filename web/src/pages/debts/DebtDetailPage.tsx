import { useParams, useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  useDebt,
  useDebtPayments,
  useDebtHistory,
  useAddDebtPayment,
  useWriteOffDebt,
  useSettleDebt,
  useCancelDebt,
} from "@/hooks";
import { formatToman, formatJalali } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { PAYMENT_METHODS } from "@/lib/constants";
import { toast } from "sonner";
import {
  ArrowLeft,
  Edit,
  CreditCard,
  Ban,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";

export default function DebtDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const debtId = Number(id);

  const { data: debt, isLoading } = useDebt(debtId);
  const { data: payments, isLoading: paymentsLoading } = useDebtPayments(debtId);
  const { data: history, isLoading: historyLoading } = useDebtHistory(debtId);

  const addPayment = useAddDebtPayment();
  const writeOff = useWriteOffDebt();
  const settle = useSettleDebt();
  const cancel = useCancelDebt();

  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [writeOffOpen, setWriteOffOpen] = useState(false);
  const [settleOpen, setSettleOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  const [paymentAmount, setPaymentAmount] = useState(0);
  const [paymentDate, setPaymentDate] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [paymentNote, setPaymentNote] = useState("");

  const handleAddPayment = () => {
    if (!paymentAmount || !paymentDate) return;
    addPayment.mutate(
      {
        debtId,
        data: {
          amount: paymentAmount,
          payment_date: paymentDate,
          payment_method: paymentMethod,
          note: paymentNote,
        },
      },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          setPaymentDialogOpen(false);
          setPaymentAmount(0);
          setPaymentDate("");
          setPaymentMethod("cash");
          setPaymentNote("");
        },
        onError: () => toast.error(t("common.error")),
      },
    );
  };

  const handleWriteOff = () => {
    writeOff.mutate(debtId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setWriteOffOpen(false);
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  const handleSettle = () => {
    settle.mutate(debtId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setSettleOpen(false);
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  const handleCancel = () => {
    cancel.mutate(debtId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setCancelOpen(false);
        navigate("/debts");
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!debt) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">{t("common.noData")}</p>
      </div>
    );
  }

  const isActive = debt.status === "active";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/debts")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">{debt.title}</h1>
          <StatusBadge status={debt.status} />
        </div>
        <div className="flex gap-2">
          {isActive && (
            <>
              <Button onClick={() => setPaymentDialogOpen(true)}>
                <CreditCard className="me-2 h-4 w-4" />
                {t("debts.addPayment")}
              </Button>
              <Link to={`/debts/${debt.id}/edit`}>
                <Button variant="outline">
                  <Edit className="me-2 h-4 w-4" />
                  {t("common.edit")}
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Debt Info Card */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("debts.detailTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("common.type")}</span>
              <StatusBadge status={debt.type} />
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("debts.counterparty")}</span>
              <span className="font-medium">{debt.counterparty_name}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("debts.originalAmount")}</span>
              <span className="font-medium">{formatToman(debt.original_amount)}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("debts.remainingAmount")}</span>
              <span className={`font-bold ${debt.remaining_amount > 0 ? "text-destructive" : "text-success"}`}>
                {formatToman(debt.remaining_amount)}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("debts.priority")}</span>
              <span className="font-medium capitalize">{debt.priority}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("common.details")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("checks.issueDate")}</span>
              <span>{formatJalali(debt.issue_date)}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("checks.dueDate")}</span>
              <span>{debt.due_date ? formatJalali(debt.due_date) : "-"}</span>
            </div>
            {debt.description && (
              <>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("common.description")}</span>
                  <span className="max-w-[200px] text-end">{debt.description}</span>
                </div>
              </>
            )}
            {debt.has_interest && (
              <>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("debts.hasInterest")}</span>
                  <span className="font-medium">
                    {debt.interest_rate ? `${debt.interest_rate}%` : "-"}
                  </span>
                </div>
              </>
            )}
            {isActive && (
              <>
                <Separator />
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={() => setSettleOpen(true)}>
                    <CheckCircle2 className="me-1 h-4 w-4" />
                    {t("debts.settle")}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setWriteOffOpen(true)}>
                    <Ban className="me-1 h-4 w-4" />
                    {t("debts.writeOff")}
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => setCancelOpen(true)}>
                    <XCircle className="me-1 h-4 w-4" />
                    {t("common.cancel")}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Payment History */}
      <Card>
        <CardHeader>
          <CardTitle>{t("debts.paymentHistory")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {paymentsLoading ? (
            <div className="p-6">
              <Skeleton className="h-32" />
            </div>
          ) : payments && payments.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("common.date")}</TableHead>
                  <TableHead>{t("common.amount")}</TableHead>
                  <TableHead>{t("common.type")}</TableHead>
                  <TableHead>{t("common.description")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell>{formatJalali(payment.payment_date)}</TableCell>
                    <TableCell className="font-medium text-success">
                      {formatToman(payment.amount)}
                    </TableCell>
                    <TableCell className="capitalize">{payment.payment_method}</TableCell>
                    <TableCell>{payment.note || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-6 text-center text-muted-foreground">{t("common.noData")}</div>
          )}
        </CardContent>
      </Card>

      {/* Status History */}
      <Card>
        <CardHeader>
          <CardTitle>{t("debts.statusHistory")}</CardTitle>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <Skeleton className="h-24" />
          ) : history && history.length > 0 ? (
            <div className="relative space-y-4 ps-6 before:absolute before:inset-y-0 before:start-2 before:w-px before:bg-border">
              {history.map((entry) => (
                <div key={entry.id} className="relative">
                  <div className="absolute -start-[1.35rem] top-1 h-3 w-3 rounded-full border-2 border-primary bg-background" />
                  <div className="rounded-lg border p-3">
                    <div className="flex items-center gap-2 text-sm">
                      <StatusBadge status={entry.old_status} />
                      <span className="text-muted-foreground">&rarr;</span>
                      <StatusBadge status={entry.new_status} />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatJalali(entry.changed_at)}
                    </p>
                    {entry.note && (
                      <p className="mt-1 text-sm">{entry.note}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground">{t("common.noData")}</p>
          )}
        </CardContent>
      </Card>

      {/* Add Payment Dialog */}
      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("debts.addPayment")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("common.amount")}</Label>
              <AmountInput
                value={paymentAmount}
                onChange={setPaymentAmount}
                placeholder={formatToman(debt.remaining_amount)}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("common.date")}</Label>
              <JalaliDatePicker
                value={paymentDate}
                onChange={setPaymentDate}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("common.type")}</Label>
              <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_METHODS.map((method) => (
                    <SelectItem key={method} value={method}>
                      {method.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t("common.description")}</Label>
              <Input
                value={paymentNote}
                onChange={(e) => setPaymentNote(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleAddPayment} disabled={addPayment.isPending || !paymentAmount || !paymentDate}>
              {addPayment.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
              {t("common.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Dialogs */}
      <ConfirmDialog
        open={writeOffOpen}
        onOpenChange={setWriteOffOpen}
        title={t("debts.writeOff")}
        description={t("common.areYouSure")}
        onConfirm={handleWriteOff}
        loading={writeOff.isPending}
      />

      <ConfirmDialog
        open={settleOpen}
        onOpenChange={setSettleOpen}
        title={t("debts.settle")}
        description={t("common.areYouSure")}
        onConfirm={handleSettle}
        loading={settle.isPending}
        variant="default"
      />

      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={t("common.cancel")}
        description={t("common.deleteConfirm")}
        onConfirm={handleCancel}
        loading={cancel.isPending}
      />
    </motion.div>
  );
}
