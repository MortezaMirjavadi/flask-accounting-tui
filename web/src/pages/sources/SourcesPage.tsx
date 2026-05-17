import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Pencil, Trash2, Landmark, ArrowRightLeft } from "lucide-react";
import {
  useSources,
  useCreateSource,
  useUpdateSource,
  useDeleteSource,
} from "@/hooks/sources";
import { sourceSchema, type SourceFormData } from "@/schemas/source";
import type { Source } from "@/types";
import { formatToman } from "@/lib/format";
import { BANK_TYPES, getBankById } from "@/lib/bankConfig";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
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

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

function BankCard({
  source,
  onEdit,
  onDelete,
  onTransfers,
}: {
  source: Source;
  onEdit: () => void;
  onDelete: () => void;
  onTransfers: () => void;
}) {
  const bank = getBankById(source.bank_type);

  return (
    <motion.div variants={fadeUp}>
      <div
        className="relative overflow-hidden rounded-xl p-5 shadow-md transition-shadow hover:shadow-lg"
        style={{ background: bank.gradient }}
      >
        {/* Bank name badge */}
        <div className="mb-4 flex items-start justify-between">
          <span
            className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold backdrop-blur-sm"
            style={{ color: bank.textColor }}
          >
            {bank.name}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onTransfers}
              className="rounded-full p-1.5 transition-colors hover:bg-white/20"
            >
              <ArrowRightLeft
                className="h-3.5 w-3.5"
                style={{ color: bank.textColor }}
              />
            </button>
            <button
              type="button"
              onClick={onEdit}
              className="rounded-full p-1.5 transition-colors hover:bg-white/20"
            >
              <Pencil
                className="h-3.5 w-3.5"
                style={{ color: bank.textColor }}
              />
            </button>
            <button
              type="button"
              onClick={onDelete}
              className="rounded-full p-1.5 transition-colors hover:bg-white/20"
            >
              <Trash2
                className="h-3.5 w-3.5"
                style={{ color: bank.textColor }}
              />
            </button>
          </div>
        </div>

        {/* Source name */}
        <p
          className="mb-1 text-sm font-medium opacity-80"
          style={{ color: bank.textColor }}
        >
          {source.name}
        </p>

        {/* Balance */}
        <p
          className="text-2xl font-bold tracking-wide"
          style={{ color: bank.textColor }}
        >
          {formatToman(source.amount)}
        </p>

        {/* Decorative circle */}
        <div
          className="absolute -bottom-6 -end-6 h-24 w-24 rounded-full opacity-10"
          style={{ backgroundColor: bank.textColor }}
        />
      </div>
    </motion.div>
  );
}

export default function SourcesPage() {
  const { t } = useTranslation();
  const { data: sourcesResp, isLoading } = useSources();
  const sources = sourcesResp?.items;
  const createMutation = useCreateSource();
  const updateMutation = useUpdateSource();
  const deleteMutation = useDeleteSource();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [deletingSource, setDeletingSource] = useState<Source | null>(null);

  const form = useForm<SourceFormData>({
    resolver: zodResolver(sourceSchema),
    defaultValues: { name: "", amount: 0, bank_type: "cash" },
  });

  function openCreate() {
    setEditingSource(null);
    form.reset({ name: "", amount: 0, bank_type: "cash" });
    setDialogOpen(true);
  }

  function openEdit(source: Source) {
    setEditingSource(source);
    form.reset({
      name: source.name,
      amount: source.amount,
      bank_type: source.bank_type || "cash",
    });
    setDialogOpen(true);
  }

  async function onSubmit(data: SourceFormData) {
    try {
      if (editingSource) {
        await updateMutation.mutateAsync({ id: editingSource.id, data });
        toast.success(t("common.success"));
      } else {
        await createMutation.mutateAsync(data);
        toast.success(t("common.success"));
      }
      setDialogOpen(false);
    } catch {
      toast.error(t("common.error"));
    }
  }

  async function handleDelete() {
    if (!deletingSource) return;
    try {
      await deleteMutation.mutateAsync(deletingSource.id);
      toast.success(t("common.success"));
      setDeletingSource(null);
    } catch {
      toast.error(t("common.error"));
    }
  }

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  const totalBalance = sources?.reduce((sum, s) => sum + +s.amount, 0) ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("sources.title")}</h1>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          {t("sources.addTitle")}
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))}
        </div>
      ) : !sources || sources.length === 0 ? (
        <p className="py-12 text-center text-muted-foreground">
          {t("common.noData")}
        </p>
      ) : (
        <>
          {/* Total Balance */}
          <Card className="border-primary/20 bg-primary/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t("dashboard.totalBalance")}
              </CardTitle>
              <Landmark className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {formatToman(totalBalance)}
              </div>
            </CardContent>
          </Card>

          {/* Bank Cards */}
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="show"
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            {sources.map((source) => (
              <BankCard
                key={source.id}
                source={source}
                onEdit={() => openEdit(source)}
                onDelete={() => setDeletingSource(source)}
                onTransfers={() =>
                  (window.location.href = `/sources/${source.id}/transfers`)
                }
              />
            ))}
          </motion.div>
        </>
      )}

      {/* Create / Edit Dialog */}
      <ResponsiveDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title={editingSource ? t("sources.editTitle") : t("sources.addTitle")}
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="bank_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sources.bank")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {BANK_TYPES.map((bank) => (
                        <SelectItem key={bank.id} value={bank.id}>
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-block h-3 w-3 rounded-full"
                              style={{ backgroundColor: bank.color }}
                            />
                            {bank.name}
                          </div>
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
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sources.sourceName")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sources.initialAmount")}</FormLabel>
                  <FormControl>
                    <AmountInput
                      value={field.value}
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={isPending}>
                {t("common.save")}
              </Button>
            </div>
          </form>
        </Form>
      </ResponsiveDialog>

      {/* Delete Confirmation Dialog */}
      <ResponsiveDialog
        open={!!deletingSource}
        onOpenChange={() => setDeletingSource(null)}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
      >
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={() => setDeletingSource(null)}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={isPending}
          >
            {t("common.delete")}
          </Button>
        </div>
      </ResponsiveDialog>
    </motion.div>
  );
}
