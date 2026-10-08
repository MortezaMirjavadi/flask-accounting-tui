import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Plus, Pencil, Trash2, ArrowLeft } from "lucide-react";
import {
  useBudgetPeriod,
  useBudgetItems,
  useCreateBudgetItem,
  useUpdateBudgetItem,
  useDeleteBudgetItem,
} from "@/hooks/budget";
import { useCategories } from "@/hooks/categories";
import type { BudgetItem } from "@/types";
import { budgetItemSchema, type BudgetItemFormData, type BudgetItemFormInput } from "@/schemas/budget";
import { PERSIAN_MONTHS } from "@/lib/constants";
import { formatToman } from "@/lib/format";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";

export default function BudgetItemsPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const periodId = Number(id);

  const { data: period, isLoading: periodLoading } = useBudgetPeriod(periodId);
  const { data: items, isLoading: itemsLoading } = useBudgetItems(periodId);
  const { data: categoriesResp } = useCategories();
  const categories = categoriesResp?.items;
  const createMutation = useCreateBudgetItem();
  const updateMutation = useUpdateBudgetItem();
  const deleteMutation = useDeleteBudgetItem();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<BudgetItem | null>(null);
  const [deletingItem, setDeletingItem] = useState<BudgetItem | null>(null);

  const form = useForm<BudgetItemFormInput, unknown, BudgetItemFormData>({
    resolver: zodResolver(budgetItemSchema),
    defaultValues: { category_id: 0, planned_amount: 0, notes: "" },
  });

  function openCreate() {
    setEditingItem(null);
    form.reset({ category_id: 0, planned_amount: 0, notes: "" });
    setDialogOpen(true);
  }

  function openEdit(item: BudgetItem) {
    setEditingItem(item);
    form.reset({
      category_id: item.category_id,
      planned_amount: item.planned_amount,
      notes: item.notes || "",
    });
    setDialogOpen(true);
  }

  async function onSubmit(data: BudgetItemFormData) {
    try {
      if (editingItem) {
        await updateMutation.mutateAsync({ id: editingItem.id, data });
      } else {
        await createMutation.mutateAsync({ ...data, budget_period_id: periodId });
      }
      toast.success(t("common.success"));
      setDialogOpen(false);
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleDelete() {
    if (!deletingItem) return;
    try {
      await deleteMutation.mutateAsync(deletingItem.id);
      toast.success(t("common.success"));
      setDeletingItem(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  const isLoading = periodLoading || itemsLoading;

  const totalPlanned = items?.reduce((sum, i) => sum + i.planned_amount, 0) ?? 0;

  const periodName = period
    ? `${PERSIAN_MONTHS[period.month - 1]} ${period.year}`
    : "";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/budget/periods")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{t("nav.budgetItems")}</h1>
            <p className="text-sm text-muted-foreground">{periodName}</p>
          </div>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          {t("budget.addItem")}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : !items || items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("common.noData")}
          </CardContent>
        </Card>
      ) : (
        <>
          <Card className="border-primary/20 bg-primary/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("budget.plannedAmount")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{formatToman(totalPlanned)}</p>
            </CardContent>
          </Card>

          <div className="space-y-2">
            {items.map((item) => (
              <Card key={item.id}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{item.category_name || `#${item.category_id}`}</p>
                    {item.notes && (
                      <p className="text-xs text-muted-foreground">{item.notes}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">{formatToman(item.planned_amount)}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => openEdit(item)}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setDeletingItem(item)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Create / Edit Dialog */}
      <ResponsiveDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title={editingItem ? t("budget.editItem") : t("budget.addItem")}
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="category_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("categories.categoryName")}</FormLabel>
                  <Select
                    onValueChange={(val) => field.onChange(Number(val))}
                    value={field.value ? String(field.value) : ""}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("common.select")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {categories?.map((cat) => (
                        <SelectItem key={cat.id} value={String(cat.id)}>
                          {cat.name} ({cat.type === "income" ? t("common.income") : t("common.cost")})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="planned_amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("budget.plannedAmount")}</FormLabel>
                  <FormControl>
                    <AmountInput value={field.value} onChange={field.onChange} onBlur={field.onBlur} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("transactions.notes")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={isPending}>
                {t("common.save")}
              </Button>
            </div>
          </form>
        </Form>
      </ResponsiveDialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deletingItem}
        onOpenChange={() => setDeletingItem(null)}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
      />
    </motion.div>
  );
}
