import { useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Search } from "lucide-react";
import {
  useCategoryTree,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "@/hooks/categories";
import { categorySchema, type CategoryFormData } from "@/schemas/category";
import type { Category } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { TreeView } from "@/components/ui/tree-view";
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

// Flatten tree for parent dropdown
function flattenTree(nodes: Category[], depth = 0): { node: Category; depth: number }[] {
  const result: { node: Category; depth: number }[] = [];
  for (const node of nodes) {
    result.push({ node, depth });
    if (node.children) {
      result.push(...flattenTree(node.children, depth + 1));
    }
  }
  return result;
}

// Filter tree nodes by search
function filterTree(nodes: Category[], query: string): Category[] {
  const q = query.toLowerCase();
  const result: Category[] = [];
  for (const node of nodes) {
    const childMatches = node.children ? filterTree(node.children, query) : [];
    const selfMatch = node.name.toLowerCase().includes(q);
    if (selfMatch || childMatches.length > 0) {
      result.push({
        ...node,
        children: selfMatch ? node.children : childMatches,
      });
    }
  }
  return result;
}

export default function CategoriesPage() {
  const { t } = useTranslation();
  const { data: tree, isLoading } = useCategoryTree();
  const createMutation = useCreateCategory();
  const updateMutation = useUpdateCategory();
  const deleteMutation = useDeleteCategory();

  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [parentForNew, setParentForNew] = useState<Category | null>(null);
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null);

  const form = useForm<CategoryFormData>({
    resolver: zodResolver(categorySchema),
    defaultValues: {
      name: "",
      type: "cost",
      parent_id: null,
    },
  });

  const treeData = tree ?? [];
  const filtered = useMemo(() => {
    if (!search.trim()) return treeData;
    return filterTree(treeData, search);
  }, [treeData, search]);

  const flatCategories = useMemo(() => flattenTree(treeData), [treeData]);

  const openCreate = useCallback(
    (parent?: Category) => {
      setEditingCategory(null);
      setParentForNew(parent ?? null);
      form.reset({
        name: "",
        type: parent?.type ?? "cost",
        parent_id: parent?.id ?? null,
      });
      setDialogOpen(true);
    },
    [form],
  );

  const openEdit = useCallback(
    (category: Category) => {
      setEditingCategory(category);
      setParentForNew(null);
      form.reset({
        name: category.name,
        type: category.type,
        parent_id: category.parent_id,
      });
      setDialogOpen(true);
    },
    [form],
  );

  async function onSubmit(data: CategoryFormData) {
    try {
      // Ensure parent_id is null (not undefined) for the API
      const payload = { ...data, parent_id: data.parent_id ?? null };
      if (editingCategory) {
        await updateMutation.mutateAsync({ id: editingCategory.id, data: payload });
        toast.success(t("common.success"));
      } else {
        await createMutation.mutateAsync(payload);
        toast.success(t("common.success"));
      }
      setDialogOpen(false);
    } catch (err: unknown) {
      let message = t("common.error");
      if (err instanceof Error && err.message) {
        message = err.message;
      }
      toast.error(message);
    }
  }

  async function handleDelete() {
    if (!deletingCategory) return;
    try {
      await deleteMutation.mutateAsync(deletingCategory.id);
      toast.success(t("common.success"));
      setDeletingCategory(null);
    } catch (err: unknown) {
      let message = t("common.error");
      if (err instanceof Error && err.message) {
        message = err.message;
      }
      toast.error(message);
    }
  }

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  // Watch the type field to lock it when adding subcategory
  const watchedType = form.watch("type");

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("categories.title")}</h1>
        <Button onClick={() => openCreate()}>
          <Plus className="h-4 w-4" />
          {t("categories.addTitle")}
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={t("common.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ps-9"
        />
      </div>

      {/* Tree View */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : (
        <div className="rounded-md border p-2">
          <TreeView
            nodes={filtered}
            onAddChild={(parent) => openCreate(parent)}
            onEdit={openEdit}
            onDelete={setDeletingCategory}
            defaultExpanded
          />
        </div>
      )}

      {/* Create / Edit Dialog */}
      <ResponsiveDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title={
          editingCategory
            ? t("categories.editTitle")
            : parentForNew
              ? `${t("categories.addTitle")} (${parentForNew.name})`
              : t("categories.addTitle")
        }
      >
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("categories.categoryName")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("categories.categoryType")}</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                    disabled={!!parentForNew}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="income">{t("common.income")}</SelectItem>
                      <SelectItem value="cost">{t("common.cost")}</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Parent selector (only when adding a root category or editing) */}
            {!parentForNew && (
              <FormField
                control={form.control}
                name="parent_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("categories.parent")}</FormLabel>
                    <Select
                      onValueChange={(val) =>
                        field.onChange(val === "none" ? null : Number(val))
                      }
                      value={field.value ? String(field.value) : "none"}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">
                          {t("categories.noParent")}
                        </SelectItem>
                        {flatCategories
                          .filter(
                            ({ node }) =>
                              !editingCategory || node.id !== editingCategory.id,
                          )
                          .map(({ node, depth }) => (
                            <SelectItem key={node.id} value={String(node.id)}>
                              {" ".repeat(depth)} {node.name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

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
        open={!!deletingCategory}
        onOpenChange={() => setDeletingCategory(null)}
        title={t("common.areYouSure")}
        description={
          deletingCategory?.children && deletingCategory.children.length > 0
            ? t("categories.deleteWithChildren")
            : t("common.deleteConfirm")
        }
      >
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={() => setDeletingCategory(null)}>
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
