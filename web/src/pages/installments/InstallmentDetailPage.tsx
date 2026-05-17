import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  useInstallmentPlan,
  useGenerateInstallments,
  useCancelInstallmentPlan,
  usePayInstallments,
  useChangeInstallmentDueDate,
} from "@/hooks";
import { formatToman, formatJalali } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { ArrowLeft, PlayCircle, XCircle, CreditCard, CalendarClock, Loader2 } from "lucide-react";

export default function InstallmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const planId = Number(id);

  const { data: plan, isLoading } = useInstallmentPlan(planId);
  const generateInstallments = useGenerateInstallments();
  const cancelPlan = useCancelInstallmentPlan();
  const payInstallments = usePayInstallments();
  const changeDueDate = useChangeInstallmentDueDate();

  const [cancelOpen, setCancelOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [payDialogOpen, setPayDialogOpen] = useState(false);
  const [dueDateDialogOpen, setDueDateDialogOpen] = useState(false);
  const [selectedInstallments, setSelectedInstallments] = useState<number[]>([]);
  const [paidDate, setPaidDate] = useState("");
  const [changeDueDateId, setChangeDueDateId] = useState<number | null>(null);
  const [newDueDate, setNewDueDate] = useState("");

  const handleGenerate = () => {
    generateInstallments.mutate(planId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setGenerateOpen(false);
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  const handleCancel = () => {
    cancelPlan.mutate(planId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setCancelOpen(false);
        navigate("/installments");
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  const handlePay = () => {
    if (selectedInstallments.length === 0 || !paidDate) return;
    payInstallments.mutate(
      { installment_ids: selectedInstallments, paid_date: paidDate },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          setPayDialogOpen(false);
          setSelectedInstallments([]);
          setPaidDate("");
        },
        onError: () => toast.error(t("common.error")),
      },
    );
  };

  const handleChangeDueDate = () => {
    if (!changeDueDateId || !newDueDate) return;
    changeDueDate.mutate(
      { id: changeDueDateId, dueDate: newDueDate },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          setDueDateDialogOpen(false);
          setChangeDueDateId(null);
          setNewDueDate("");
        },
        onError: () => toast.error(t("common.error")),
      },
    );
  };

  const toggleInstallment = (installmentId: number) => {
    setSelectedInstallments((prev) =>
      prev.includes(installmentId)
        ? prev.filter((id) => id !== installmentId)
        : [...prev, installmentId],
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">{t("common.noData")}</p>
      </div>
    );
  }

  // Extract installments from plan if available
  const installments = (plan as Record<string, unknown>).installments as
    | Array<{
        id: number;
        installment_number: number;
        amount: number;
        due_date: string;
        paid_date: string | null;
        status: string;
      }>
    | undefined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/installments")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">{plan.title}</h1>
          <StatusBadge status={plan.status} />
        </div>
        <div className="flex gap-2">
          {plan.status === "active" && (
            <>
              <Button variant="outline" onClick={() => setGenerateOpen(true)}>
                <PlayCircle className="me-2 h-4 w-4" />
                {t("installments.generate")}
              </Button>
              <Button variant="destructive" onClick={() => setCancelOpen(true)}>
                <XCircle className="me-2 h-4 w-4" />
                {t("common.cancel")}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Plan Info */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("installments.totalAmount")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatToman(plan.total_amount)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("installments.installmentCount")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{plan.installment_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("installments.installmentAmount")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatToman(plan.installment_amount)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("installments.dueDayOfMonth")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{plan.due_day_of_month}</p>
          </CardContent>
        </Card>
      </div>

      {/* Installments Table */}
      {installments && installments.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t("installments.title")}</CardTitle>
            {selectedInstallments.length > 0 && (
              <Button onClick={() => setPayDialogOpen(true)}>
                <CreditCard className="me-2 h-4 w-4" />
                {t("installments.pay")} ({selectedInstallments.length})
              </Button>
            )}
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">#</TableHead>
                  <TableHead>{t("installments.installmentAmount")}</TableHead>
                  <TableHead>{t("checks.dueDate")}</TableHead>
                  <TableHead>{t("common.paid")}</TableHead>
                  <TableHead>{t("common.status")}</TableHead>
                  <TableHead className="text-end">{t("common.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {installments.map((inst) => (
                  <TableRow key={inst.id}>
                    <TableCell>
                      {inst.status === "pending" || inst.status === "overdue" ? (
                        <input
                          type="checkbox"
                          checked={selectedInstallments.includes(inst.id)}
                          onChange={() => toggleInstallment(inst.id)}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                      ) : (
                        inst.installment_number
                      )}
                    </TableCell>
                    <TableCell>{formatToman(inst.amount)}</TableCell>
                    <TableCell>{formatJalali(inst.due_date)}</TableCell>
                    <TableCell>{inst.paid_date ? formatJalali(inst.paid_date) : "-"}</TableCell>
                    <TableCell>
                      <StatusBadge status={inst.status} />
                    </TableCell>
                    <TableCell className="text-end">
                      {(inst.status === "pending" || inst.status === "overdue") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setChangeDueDateId(inst.id);
                            setNewDueDate(inst.due_date);
                            setDueDateDialogOpen(true);
                          }}
                        >
                          <CalendarClock className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Cancel Dialog */}
      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
        onConfirm={handleCancel}
        loading={cancelPlan.isPending}
      />

      {/* Generate Dialog */}
      <ConfirmDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        title={t("installments.generate")}
        description={t("common.areYouSure")}
        onConfirm={handleGenerate}
        loading={generateInstallments.isPending}
        variant="default"
      />

      {/* Pay Dialog */}
      <Dialog open={payDialogOpen} onOpenChange={setPayDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("installments.pay")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("common.paid")}</Label>
              <JalaliDatePicker
                value={paidDate}
                onChange={setPaidDate}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handlePay} disabled={payInstallments.isPending || !paidDate}>
              {payInstallments.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
              {t("common.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Change Due Date Dialog */}
      <Dialog open={dueDateDialogOpen} onOpenChange={setDueDateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("installments.dueDayOfMonth")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("checks.dueDate")}</Label>
              <JalaliDatePicker
                value={newDueDate}
                onChange={setNewDueDate}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDueDateDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleChangeDueDate} disabled={changeDueDate.isPending || !newDueDate}>
              {changeDueDate.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
