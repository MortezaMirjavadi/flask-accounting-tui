import { useNavigate, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { useWalletContext } from "@/context/wallet-context";
import { useCreateDebt, useUpdateDebt, useDebt, useCategoryTree } from "@/hooks";
import { debtSchema, type DebtFormData, type DebtFormInput } from "@/schemas/debt";
import {
  DEBT_TYPES,
  PRIORITY_LEVELS,
  COUNTERPARTY_TYPES,
} from "@/lib/constants";
import { useIsMobile } from "@/hooks/use-mobile";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { CategoryTreeSelect } from "@/components/shared/CategoryTreeSelect";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";
import { Loader2, ArrowLeft } from "lucide-react";
import { COUNTERPARTY_TYPE_LABELS } from "@/lib/enum-labels";
import type { TranslationKey } from "@/types/i18next";

/** Locale keys for the interest-type enum required by the backend. */
const INTEREST_TYPE_LABELS: Record<"simple" | "compound" | "fixed", TranslationKey> = {
  simple: "debts.interestSimple",
  compound: "debts.interestCompound",
  fixed: "debts.interestFixed",
};

export default function DebtFormPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const isEditing = !!id;
  const debtId = Number(id);
  const isMobile = useIsMobile();

  const { data: existingDebt, isLoading: debtLoading } = useDebt(debtId);
  const createDebt = useCreateDebt();
  const updateDebt = useUpdateDebt();
  const { activeWallet } = useWalletContext();

  const form = useForm<DebtFormInput, unknown, DebtFormData>({
    resolver: zodResolver(debtSchema),
    defaultValues: {
      type: "payable",
      counterparty_name: "",
      counterparty_type: "person",
      title: "",
      description: "",
      original_amount: 0,
      issue_date: "",
      due_date: "",
      priority: "medium",
      category_id: null,
      has_interest: false,
      interest_type: "simple",
      interest_rate: null,
    },
  });

  // Category is used when registering payment transactions:
  // payable debts pay out (cost categories), receivables pay in (income).
  const debtType = useWatch({ control: form.control, name: "type" });
  const categoryFilterType = debtType === "receivable" ? "income" : "cost";
  const { data: categoriesTree } = useCategoryTree({ type: categoryFilterType });

  useEffect(() => {
    if (isEditing && existingDebt) {
      form.reset({
        type: existingDebt.type,
        counterparty_name: existingDebt.counterparty_name,
        counterparty_type: existingDebt.counterparty_type || "person",
        title: existingDebt.title,
        description: existingDebt.description || "",
        original_amount: existingDebt.original_amount,
        issue_date: existingDebt.issue_date,
        due_date: existingDebt.due_date || "",
        priority: existingDebt.priority || "medium",
        category_id: existingDebt.category_id ?? null,
        has_interest: existingDebt.has_interest || false,
        interest_type: (existingDebt.interest_type as "simple" | "compound" | "fixed") || "simple",
        interest_rate: existingDebt.interest_rate,
      });
    }
  }, [existingDebt, isEditing, form]);

  const onSubmit = (data: DebtFormData) => {
    // Surface the backend's error message (ApiError.message) in the toast.
    const onError = (err: unknown) =>
      toast.error(err instanceof Error && err.message ? err.message : t("common.error"));
    // Bind the debt to the active wallet so it appears in the wallet-scoped
    // list; on edit, keep the debt's original wallet if it has one.
    const payload = {
      ...data,
      wallet_id: isEditing ? (existingDebt?.wallet_id ?? activeWallet?.id) : activeWallet?.id,
    };
    if (isEditing) {
      updateDebt.mutate(
        { id: debtId, data: payload },
        {
          onSuccess: () => {
            toast.success(t("common.success"));
            navigate(`/debts/${debtId}`);
          },
          onError,
        },
      );
    } else {
      createDebt.mutate(payload, {
        onSuccess: () => {
          toast.success(t("common.success"));
          navigate("/debts");
        },
        onError,
      });
    }
  };

  const isPending = createDebt.isPending || updateDebt.isPending;

  if (isEditing && debtLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="space-y-4 pt-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  const formContent = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          <FormField
            control={form.control}
            name="type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("common.type")}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {DEBT_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {t(`debts.${type}`)}
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
            name="priority"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("debts.priority")}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {PRIORITY_LEVELS.map((level) => (
                      <SelectItem key={level} value={level}>
                        {t(`debts.${level}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("common.name")}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          <FormField
            control={form.control}
            name="counterparty_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("debts.counterparty")}</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="counterparty_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("debts.counterpartyType")}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {COUNTERPARTY_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {t(COUNTERPARTY_TYPE_LABELS[type])}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="category_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("transactions.category")}</FormLabel>
              <div className="flex items-center gap-2">
                <FormControl>
                  <CategoryTreeSelect
                    categories={categoriesTree ?? []}
                    value={field.value ?? undefined}
                    onChange={field.onChange}
                    placeholder={t("common.select")}
                  />
                </FormControl>
                {field.value != null && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => field.onChange(null)}
                  >
                    {t("common.clear")}
                  </Button>
                )}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="original_amount"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("debts.originalAmount")}</FormLabel>
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

        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          <FormField
            control={form.control}
            name="issue_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("checks.issueDate")}</FormLabel>
                <FormControl>
                  <JalaliDatePicker
                    value={field.value}
                    onChange={field.onChange}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="due_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("checks.dueDate")}</FormLabel>
                <FormControl>
                  <JalaliDatePicker
                    value={field.value || ""}
                    onChange={field.onChange}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("common.description")}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="has_interest"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <FormLabel>{t("debts.hasInterest")}</FormLabel>
              </div>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
            </FormItem>
          )}
        />

        {form.watch("has_interest") && (
          <>
          <FormField
            control={form.control}
            name="interest_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("debts.interestType")}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value ?? "simple"}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {(Object.keys(INTEREST_TYPE_LABELS) as Array<keyof typeof INTEREST_TYPE_LABELS>).map((type) => (
                      <SelectItem key={type} value={type}>
                        {t(INTEREST_TYPE_LABELS[type])}
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
            name="interest_rate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("debts.interestRate")}</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value ? Number(e.target.value) : null,
                      )
                    }
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          </>
        )}

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/debts")}
          >
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
            {isEditing ? t("common.update") : t("common.save")}
          </Button>
        </div>
      </form>
    </Form>
  );

  if (isMobile) {
    return (
      <Sheet
        open={true}
        onOpenChange={(open) => !open && navigate(-1)}
        direction="bottom"
      >
        <SheetContent
          side="bottom"
          className="max-h-[90vh] overflow-y-auto px-4 pb-8"
        >
          <SheetHeader className="text-start">
            <SheetTitle>
              {isEditing ? t("debts.editTitle") : t("debts.addTitle")}
            </SheetTitle>
          </SheetHeader>
          {formContent}
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate("/debts")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">
            {isEditing ? t("debts.editTitle") : t("debts.addTitle")}
          </h1>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {isEditing ? t("debts.editTitle") : t("debts.addTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent>{formContent}</CardContent>
      </Card>
    </motion.div>
  );
}
