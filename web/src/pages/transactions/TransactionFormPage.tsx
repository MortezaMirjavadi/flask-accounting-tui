import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm, useFieldArray, useWatch } from "react-hook-form";
import { Plus, Trash2, Loader2, ArrowLeft, EyeOff } from "lucide-react";
import {
  useTransaction,
  useCreateTransaction,
  useUpdateTransaction,
  useCreateTransfer,
} from "@/hooks/transactions";
import { useCategories } from "@/hooks/categories";
import { useSources } from "@/hooks/sources";
import { useAccounts } from "@/hooks/accounts";
import { useWalletContext } from "@/context/wallet-context";
import {
  transactionSchema,
  transferSchema,
  type TransactionFormData,
  type TransferFormData,
} from "@/schemas/transaction";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { AmountInput } from "@/components/shared/AmountInput";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
import { formatToman, numberToPersianWords, toPersianDigits } from "@/lib/format";
import i18n from "@/i18n";
import { getBankById } from "@/lib/bankConfig";
import { toast } from "sonner";

/** Format a number string with commas: "1000000" -> "1,000,000" */
function addCommas(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (!digits) return "";
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** Remove commas and return the raw number string */
function removeCommas(value: string): string {
  return value.replace(/,/g, "");
}

interface CombinedFormData {
  date: string;
  amount: number;
  category_id: number;
  source_id: number;
  account_id?: number;
  wallet_id?: number;
  is_private: boolean;
  description: string;
  items: TransactionFormData["items"];
  from_account_id: number;
  to_account_id: number;
  notes: string;
}

export default function TransactionFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const isEdit = !!id;
  const isMobile = useIsMobile();

  // Active wallet from header switcher
  const { activeWallet } = useWalletContext();

  const { data: transaction, isLoading: txLoading } = useTransaction(
    Number(id) || 0,
  );
  const { data: categoriesResp, isLoading: categoriesLoading } = useCategories();
  const { data: sourcesResp, isLoading: sourcesLoading } = useSources();
  const categories = categoriesResp?.items;
  const sources = sourcesResp?.items;
  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const createTransferMutation = useCreateTransfer();

  // Accounts for the active wallet
  const { data: activeWalletAccounts, isLoading: accountsLoading } =
    useAccounts(activeWallet?.id ?? 0);

  // Determine if the active wallet is shared (for private toggle)
  const isSharedWallet = activeWallet?.wallet_type === "shared";

  // For edit mode, load accounts of the transaction's original wallet
  const [editWalletId, setEditWalletId] = useState<number | null>(null);
  const { data: editWalletAccounts } = useAccounts(editWalletId ?? 0);

  // Use active wallet accounts in create mode, edit wallet accounts in edit mode
  const currentAccounts = isEdit ? editWalletAccounts : activeWalletAccounts;
  const currentWalletId = isEdit
    ? (editWalletId ?? transaction?.wallet_id)
    : activeWallet?.id;

  const [itemsEnabled, setItemsEnabled] = useState(false);
  const [isTransfer, setIsTransfer] = useState(
    searchParams.get("transfer") === "true",
  );
  const [amountDisplay, setAmountDisplay] = useState("");
  const [transferWalletId, setTransferWalletId] = useState<number | null>(
    activeWallet?.id ?? null,
  );
  const { data: transferWalletAccounts } = useAccounts(transferWalletId ?? 0);

  const form = useForm<CombinedFormData>({
    defaultValues: {
      date: new Date().toISOString().split("T")[0],
      amount: 0,
      category_id: 0,
      source_id: 0,
      account_id: undefined,
      wallet_id: undefined,
      is_private: false,
      description: "",
      items: [],
      from_account_id: 0,
      to_account_id: 0,
      notes: "",
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "items",
  });

  const watchAmount = useWatch({ control: form.control, name: "amount" });

  useEffect(() => {
    if (isEdit && transaction) {
      form.reset({
        date: transaction.date,
        amount: transaction.amount,
        category_id: transaction.category_id,
        source_id: transaction.source_id,
        account_id: transaction.account_id,
        wallet_id: transaction.wallet_id,
        is_private: transaction.is_private ?? false,
        description: transaction.description || "",
        items: [],
        from_account_id: 0,
        to_account_id: 0,
        notes: "",
      });
      setAmountDisplay(addCommas(String(Math.floor(transaction.amount))));
      if (transaction.wallet_id) {
        setEditWalletId(transaction.wallet_id);
      }
    }
  }, [isEdit, transaction, form]);

  async function onSubmit(data: CombinedFormData) {
    try {
      if (isTransfer) {
        const transferData: TransferFormData = {
          from_account_id: data.from_account_id,
          to_account_id: data.to_account_id,
          amount: data.amount,
          date: data.date,
          notes: data.notes,
        };
        const result = transferSchema.safeParse(transferData);
        if (!result.success) {
          result.error.issues.forEach((issue) => {
            const field = issue.path[0] as keyof CombinedFormData;
            form.setError(field, { message: issue.message });
          });
          return;
        }
        await createTransferMutation.mutateAsync(result.data);
        toast.success(t("common.success"));
        navigate("/transfers");
      } else {
        // Determine source_id and account_id
        // If account was selected (from active wallet), use wallet_id as source_id
        const finalSourceId = data.account_id
          ? (currentWalletId ?? data.source_id)
          : data.source_id;

        const txData = {
          date: data.date,
          amount: data.amount,
          category_id: data.category_id,
          source_id: finalSourceId,
          account_id: data.account_id,
          wallet_id: currentWalletId,
          is_private: data.is_private,
          description: data.description,
          items: itemsEnabled ? data.items : [],
        };
        const result = transactionSchema.safeParse(txData);
        if (!result.success) {
          result.error.issues.forEach((issue) => {
            const field = issue.path[0] as keyof CombinedFormData;
            form.setError(field, { message: issue.message });
          });
          return;
        }
        if (isEdit) {
          await updateMutation.mutateAsync({
            id: Number(id),
            data: result.data,
          });
          toast.success(t("common.success"));
          navigate(`/transactions/${id}`);
        } else {
          await createMutation.mutateAsync(result.data);
          toast.success(t("common.success"));
          navigate("/transactions");
        }
      }
    } catch {
      toast.error(t("common.error"));
    }
  }

  function toggleTransfer(value: boolean) {
    setIsTransfer(value);
    form.clearErrors();
    if (value) {
      form.setValue("category_id", 0);
      form.setValue("source_id", 0);
      form.setValue("account_id", undefined);
      form.setValue("description", "");
      form.setValue("items", []);
      setItemsEnabled(false);
    } else {
      form.setValue("from_source_id", 0);
      form.setValue("to_source_id", 0);
      form.setValue("notes", "");
    }
  }

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    createTransferMutation.isPending;
  const isLoading = isTransfer
    ? txLoading || sourcesLoading
    : txLoading || categoriesLoading || sourcesLoading || accountsLoading;

  if (isEdit && isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
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
        {!isEdit && (
          <div className="flex rounded-lg border p-1">
            <button
              type="button"
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                !isTransfer
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted"
              }`}
              onClick={() => toggleTransfer(false)}
            >
              {t("transactions.transferFrom")}
            </button>
            <button
              type="button"
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                isTransfer
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted"
              }`}
              onClick={() => toggleTransfer(true)}
            >
              {t("transactions.transfer")}
            </button>
          </div>
        )}

        {/* Date & Amount */}
        <div className="grid gap-4 grid-cols-2">
          <FormField
            control={form.control}
            name="date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("common.date")}</FormLabel>
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
            name="amount"
            render={() => (
              <FormItem>
                <FormLabel>{t("common.amount")}</FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    inputMode="numeric"
                    dir="ltr"
                    value={i18n.language === "fa" ? toPersianDigits(amountDisplay) : amountDisplay}
                    placeholder={i18n.language === "fa" ? "۰" : "0"}
                    onChange={(e) => {
                      // Convert Persian digits to Latin for processing
                      const input = e.target.value.replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)));
                      const raw = removeCommas(input);
                      if (!/^\d*$/.test(raw)) return;
                      setAmountDisplay(addCommas(raw));
                      form.setValue("amount", raw ? Number(raw) : 0);
                    }}
                    onBlur={() => {
                      const raw = removeCommas(amountDisplay);
                      form.setValue("amount", raw ? Number(raw) : 0);
                    }}
                  />
                </FormControl>
                {watchAmount > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {numberToPersianWords(watchAmount)} تومان
                  </p>
                )}
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Source / Account & Category */}
        {isTransfer ? (
          <div className="grid gap-4 grid-cols-3">
            <FormField
              control={form.control}
              name="from_account_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("wallets.wallet")}</FormLabel>
                  <Select
                    onValueChange={(val) => {
                      const numVal = Number(val);
                      setTransferWalletId(numVal);
                      form.setValue("from_account_id", 0);
                      form.setValue("to_account_id", 0);
                    }}
                    value={transferWalletId ? String(transferWalletId) : ""}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("common.select")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {sources?.map((src) => (
                        <SelectItem key={src.id} value={String(src.id)}>
                          {src.name}
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
              name="from_account_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("transactions.transferFrom")}</FormLabel>
                  <Select
                    onValueChange={(val) => field.onChange(Number(val))}
                    value={field.value ? String(field.value) : ""}
                    disabled={!transferWalletId}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("common.select")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {transferWalletAccounts?.map((acc) => {
                        const bank = getBankById(acc.bank_type);
                        return (
                          <SelectItem key={acc.id} value={String(acc.id)}>
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                                style={{ backgroundColor: bank.color }}
                              />
                              <span className="truncate">{acc.name}</span>
                              <span className="ms-auto text-xs text-muted-foreground">
                                {formatToman(acc.amount)}
                              </span>
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="to_account_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("transactions.transferTo")}</FormLabel>
                  <Select
                    onValueChange={(val) => field.onChange(Number(val))}
                    value={field.value ? String(field.value) : ""}
                    disabled={!transferWalletId}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("common.select")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {transferWalletAccounts
                        ?.filter((acc) => acc.id !== form.watch("from_account_id"))
                        .map((acc) => {
                          const bank = getBankById(acc.bank_type);
                          return (
                            <SelectItem key={acc.id} value={String(acc.id)}>
                              <div className="flex items-center gap-2">
                                <span
                                  className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                                  style={{ backgroundColor: bank.color }}
                                />
                                <span className="truncate">{acc.name}</span>
                                <span className="ms-auto text-xs text-muted-foreground">
                                  {formatToman(acc.amount)}
                                </span>
                              </div>
                            </SelectItem>
                          );
                        })}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-2">
            {/* Source selector: accounts of active wallet when available, otherwise flat wallet list */}
            <FormField
              control={form.control}
              name="account_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("transactions.source")}</FormLabel>
                  <Select
                    onValueChange={(val) => {
                      const numVal = Number(val);
                      field.onChange(numVal);
                      // Set source_id to wallet_id for backward compat
                      if (currentWalletId) {
                        form.setValue("source_id", currentWalletId);
                        form.setValue("wallet_id", currentWalletId);
                      } else {
                        form.setValue("source_id", numVal);
                      }
                    }}
                    value={
                      currentWalletId &&
                      currentAccounts &&
                      currentAccounts.length > 0
                        ? field.value
                          ? String(field.value)
                          : ""
                        : form.watch("source_id")
                          ? String(form.watch("source_id"))
                          : ""
                    }
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("common.select")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {currentWalletId &&
                      currentAccounts &&
                      currentAccounts.length > 0
                        ? // Show accounts of the active wallet
                          currentAccounts.map((acc) => {
                            const bank = getBankById(acc.bank_type);
                            return (
                              <SelectItem key={acc.id} value={String(acc.id)}>
                                <div className="flex items-center gap-2">
                                  <span
                                    className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                                    style={{ backgroundColor: bank.color }}
                                  />
                                  <span className="truncate">{acc.name}</span>
                                  <span className="ms-auto text-xs text-muted-foreground">
                                    {formatToman(acc.amount)}
                                  </span>
                                </div>
                              </SelectItem>
                            );
                          })
                        : // Fallback: flat wallet list
                          (sources?.map((src) => {
                            const bank = getBankById(src.bank_type);
                            return (
                              <SelectItem key={src.id} value={String(src.id)}>
                                <div className="flex items-center gap-2">
                                  <span
                                    className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                                    style={{ backgroundColor: bank.color }}
                                  />
                                  <span className="truncate">{src.name}</span>
                                  <span className="ms-auto text-xs text-muted-foreground">
                                    {formatToman(src.amount)}
                                  </span>
                                </div>
                              </SelectItem>
                            );
                          }) ?? [])}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Category selector */}
            <FormField
              control={form.control}
              name="category_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("transactions.category")}</FormLabel>
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
                          {cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}

        {/* Description / Notes */}
        {isTransfer ? (
          <FormField
            control={form.control}
            name="notes"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("transactions.notes")}</FormLabel>
                <FormControl>
                  <Textarea {...field} rows={3} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        ) : (
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("common.description")}</FormLabel>
                <FormControl>
                  <Textarea {...field} rows={3} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        {/* Private transaction toggle for shared wallets */}
        {!isTransfer && isSharedWallet && (
          <FormField
            control={form.control}
            name="is_private"
            render={({ field }) => (
              <FormItem>
                <label className="flex items-center gap-2 cursor-pointer rounded-lg border p-3">
                  <input
                    type="checkbox"
                    checked={field.value ?? false}
                    onChange={(e) => field.onChange(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-1.5 text-sm font-medium">
                      <EyeOff className="h-3.5 w-3.5" />
                      {t("wallets.privateTransaction")}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {t("wallets.privateHint")}
                    </p>
                  </div>
                </label>
              </FormItem>
            )}
          />
        )}

        {/* Line Items Section */}
        {!isTransfer && (
          <>
            <Separator />
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {t("transactions.items")}
              </span>
              {!itemsEnabled ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setItemsEnabled(true)}
                >
                  <Plus className="h-4 w-4" />
                  {t("transactions.addItem")}
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setItemsEnabled(false);
                    form.setValue("items", []);
                  }}
                >
                  {t("common.remove")}
                </Button>
              )}
            </div>
            {itemsEnabled && (
              <div className="space-y-3">
                {fields.map((field, index) => (
                  <div
                    key={field.id}
                    className="rounded-lg border p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">
                        #{index + 1}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => remove(index)}
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    </div>
                    <div className="grid gap-2 grid-cols-2">
                      <FormField
                        control={form.control}
                        name={`items.${index}.name`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">
                              {t("transactions.itemName")}
                            </FormLabel>
                            <FormControl>
                              <Input {...field} className="h-8 text-xs" />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`items.${index}.quantity`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">
                              {t("transactions.quantity")}
                            </FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                {...field}
                                className="h-8 text-xs"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`items.${index}.unit`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">
                              {t("transactions.unit")}
                            </FormLabel>
                            <FormControl>
                              <Input {...field} className="h-8 text-xs" />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`items.${index}.unit_price`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs">
                              {t("transactions.unitPrice")}
                            </FormLabel>
                            <FormControl>
                              <AmountInput
                                value={field.value}
                                onChange={field.onChange}
                                onBlur={field.onBlur}
                                className="h-8 text-xs"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() =>
                    append({
                      name: "",
                      quantity: 1,
                      unit: "",
                      unit_price: 0,
                      total_price: 0,
                      notes: "",
                    })
                  }
                >
                  <Plus className="h-4 w-4" />
                  {t("transactions.addItem")}
                </Button>
              </div>
            )}
          </>
        )}

        {/* Submit */}
        <Button type="submit" className="w-full" size="lg" disabled={isPending}>
          {isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
          {isEdit ? t("common.update") : t("common.save")}
        </Button>
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
              {isEdit
                ? t("transactions.editTitle")
                : isTransfer
                  ? t("transactions.transfer")
                  : t("transactions.addTitle")}
            </SheetTitle>
          </SheetHeader>
          {formContent}
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="mx-auto max-w-xl space-y-4"
    >
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-xl font-bold">
          {isEdit
            ? t("transactions.editTitle")
            : isTransfer
              ? t("transactions.transfer")
              : t("transactions.addTitle")}
        </h1>
      </div>

      <Card>
        <CardContent className="p-4">{formContent}</CardContent>
      </Card>
    </motion.div>
  );
}
