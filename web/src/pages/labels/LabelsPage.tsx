import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  useLabels,
  useCreateLabel,
  useUpdateLabel,
  useDeleteLabel,
} from "@/hooks";
import { labelSchema, type LabelFormData } from "@/schemas/metadata";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ResponsiveDialog } from "@/components/shared/ResponsiveDialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import type { Label } from "@/types";

export default function LabelsPage() {
  const { t } = useTranslation();
  const { data: labelsResp, isLoading } = useLabels();
  const labels = labelsResp?.items;
  const createLabel = useCreateLabel();
  const updateLabel = useUpdateLabel();
  const deleteLabel = useDeleteLabel();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingLabel, setEditingLabel] = useState<Label | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const form = useForm<LabelFormData>({
    resolver: zodResolver(labelSchema),
    defaultValues: {
      name: "",
      color: "#3b82f6",
    },
  });

  const openCreate = () => {
    setEditingLabel(null);
    form.reset({ name: "", color: "#3b82f6" });
    setDialogOpen(true);
  };

  const openEdit = (label: Label) => {
    setEditingLabel(label);
    form.reset({ name: label.name, color: label.color || "#3b82f6" });
    setDialogOpen(true);
  };

  const handleDelete = (id: number) => {
    setDeletingId(id);
    setDeleteOpen(true);
  };

  const confirmDelete = () => {
    if (!deletingId) return;
    deleteLabel.mutate(deletingId, {
      onSuccess: () => {
        toast.success(t("common.success"));
        setDeleteOpen(false);
        setDeletingId(null);
      },
      onError: () => toast.error(t("common.error")),
    });
  };

  const onSubmit = (data: LabelFormData) => {
    if (editingLabel) {
      updateLabel.mutate(
        { id: editingLabel.id, data },
        {
          onSuccess: () => {
            toast.success(t("common.success"));
            setDialogOpen(false);
          },
          onError: () => toast.error(t("common.error")),
        },
      );
    } else {
      createLabel.mutate(data, {
        onSuccess: () => {
          toast.success(t("common.success"));
          setDialogOpen(false);
        },
        onError: () => toast.error(t("common.error")),
      });
    }
  };

  const isPending = createLabel.isPending || updateLabel.isPending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("metadata.labels")}</h1>
        <Button onClick={openCreate}>
          <Plus className="me-2 h-4 w-4" />
          {t("metadata.addLabel")}
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="flex items-center gap-3 p-4">
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : labels && labels.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {labels.map((label) => (
            <Card key={label.id} className="group">
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div
                    className="h-8 w-8 rounded-full border"
                    style={{ backgroundColor: label.color || "#3b82f6" }}
                  />
                  <span className="font-medium">{label.name}</span>
                </div>
                <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(label)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(label.id)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent>
            <EmptyState titleKey="common.noData" descriptionKey="metadata.addLabel" />
          </CardContent>
        </Card>
      )}

      {/* Create / Edit Dialog */}
      <ResponsiveDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title={editingLabel ? t("metadata.editLabel") : t("metadata.addLabel")}
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("metadata.labelName")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("metadata.color")}</FormLabel>
                  <FormControl>
                    <div className="flex items-center gap-3">
                      <Input
                        type="color"
                        {...field}
                        className="h-10 w-16 cursor-pointer p-1"
                      />
                      <Input
                        value={field.value}
                        onChange={field.onChange}
                        placeholder="#3b82f6"
                        className="flex-1"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                {t("common.save")}
              </Button>
            </div>
          </form>
        </Form>
      </ResponsiveDialog>

      {/* Delete Confirm */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t("common.areYouSure")}
        description={t("common.deleteConfirm")}
        onConfirm={confirmDelete}
        loading={deleteLabel.isPending}
      />
    </motion.div>
  );
}
