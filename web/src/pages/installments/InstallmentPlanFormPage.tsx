import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { useWalletContext } from "@/context/wallet-context";
import { useCreateInstallmentPlan, useCategoryTree } from "@/hooks";
import { installmentPlanSchema, type InstallmentPlanFormData, type InstallmentPlanFormInput } from "@/schemas/installment";
import { useIsMobile } from "@/hooks/use-mobile";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { CategoryTreeSelect } from "@/components/shared/CategoryTreeSelect";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
import { formatNumber, toSafeNumber } from "@/lib/format";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { toast } from "sonner";
import { Loader2, ArrowLeft } from "lucide-react";

export default function InstallmentPlanFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const createPlan = useCreateInstallmentPlan();
  const { data: categoriesTree } = useCategoryTree();
  const { activeWallet } = useWalletContext();
  const isMobile = useIsMobile();

  const form = useForm<InstallmentPlanFormInput, unknown, InstallmentPlanFormData>({
    resolver: zodResolver(installmentPlanSchema),
    defaultValues: {
      title: "",
      total_amount: 0,
      installment_count: 1,
      installment_amount: 0,
      start_date: "",
      due_day_of_month: 1,
    },
  });

  const totalAmount = form.watch("total_amount");
  const installmentCount = form.watch("installment_count");

  const onSubmit = (data: InstallmentPlanFormData) => {
    // Bind the plan to the active wallet so it appears in the wallet-scoped
    // plans list (the TUI requires a wallet at creation too).
    createPlan.mutate({ ...data, wallet_id: activeWallet?.id }, {
      onSuccess: () => {
        toast.success(t("common.success"));
        navigate("/installments");
      },
      onError: (err) => {
        toast.error(
          err instanceof Error && err.message
            ? err.message
            : t("common.error"),
        );
      },
    });
  };

  const formContent = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("installments.planTitle")}</FormLabel>
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
            name="total_amount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("installments.totalAmount")}</FormLabel>
                <FormControl>
                  <AmountInput value={field.value} onChange={field.onChange} onBlur={field.onBlur} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="installment_count"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("installments.installmentCount")}</FormLabel>
                <FormControl>
                  <Input type="number" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="installment_amount"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("installments.installmentAmount")}</FormLabel>
              <FormControl>
                <AmountInput value={field.value} onChange={field.onChange} onBlur={field.onBlur} />
              </FormControl>
              {totalAmount > 0 && installmentCount > 0 && (
                <p className="text-sm text-muted-foreground">
                  {t("installments.suggestedAmount", {
                    amount: formatNumber(
                      Math.ceil(
                        toSafeNumber(totalAmount) / Math.max(toSafeNumber(installmentCount), 1)
                      )
                    ),
                  })}
                </p>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          <FormField
            control={form.control}
            name="start_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("installments.startDate")}</FormLabel>
                <FormControl>
                  <JalaliDatePicker value={field.value} onChange={field.onChange} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="due_day_of_month"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("installments.dueDayOfMonth")}</FormLabel>
                <FormControl>
                  <Input type="number" min={1} max={31} {...field} />
                </FormControl>
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
              <FormControl>
                <CategoryTreeSelect
                  categories={categoriesTree ?? []}
                  value={field.value || undefined}
                  onChange={field.onChange}
                  placeholder={t("common.select")}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/installments")}
          >
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={createPlan.isPending}>
            {createPlan.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
            {t("common.save")}
          </Button>
        </div>
      </form>
    </Form>
  );

  if (isMobile) {
    return (
      <Sheet open={true} onOpenChange={(open) => !open && navigate(-1)} direction="bottom">
        <SheetContent side="bottom" className="max-h-[90vh] overflow-y-auto px-4 pb-8">
          <SheetHeader className="text-start">
            <SheetTitle>{t("installments.addPlan")}</SheetTitle>
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
          <Button variant="ghost" size="icon" onClick={() => navigate("/installments")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">{t("installments.addPlan")}</h1>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("installments.addPlan")}</CardTitle>
        </CardHeader>
        <CardContent>
          {formContent}
        </CardContent>
      </Card>
    </motion.div>
  );
}
