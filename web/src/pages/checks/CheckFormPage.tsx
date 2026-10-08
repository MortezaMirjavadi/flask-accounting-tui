import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { useWalletContext } from "@/context/wallet-context";
import { useCreateCheck, useCategoryTree } from "@/hooks";
import { checkSchema, type CheckFormData, type CheckFormInput } from "@/schemas/check";
import { CHECK_TYPES } from "@/lib/constants";
import { useIsMobile } from "@/hooks/use-mobile";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmountInput } from "@/components/shared/AmountInput";
import { CategoryTreeSelect } from "@/components/shared/CategoryTreeSelect";
import { JalaliDatePicker } from "@/components/shared/JalaliDatePicker";
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
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { toast } from "sonner";
import { Loader2, ArrowLeft } from "lucide-react";

export default function CheckFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const createCheck = useCreateCheck();
  const { data: categoriesTree } = useCategoryTree();
  const { activeWallet } = useWalletContext();
  const isMobile = useIsMobile();

  const form = useForm<CheckFormInput, unknown, CheckFormData>({
    resolver: zodResolver(checkSchema),
    defaultValues: {
      check_number: "",
      bank_name: "",
      amount: 0,
      issue_date: "",
      due_date: "",
      type: "issued",
      description: "",
    },
  });

  const onSubmit = (data: CheckFormData) => {
    // Bind the check to the active wallet so it appears in the wallet-scoped
    // checks list.
    createCheck.mutate({ ...data, wallet_id: activeWallet?.id }, {
      onSuccess: () => {
        toast.success(t("common.success"));
        navigate("/checks");
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
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          <FormField
            control={form.control}
            name="check_number"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("checks.checkNumber")}</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="bank_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("checks.bankName")}</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="amount"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("common.amount")}</FormLabel>
              <FormControl>
                <AmountInput value={field.value} onChange={field.onChange} onBlur={field.onBlur} />
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
                  <JalaliDatePicker value={field.value} onChange={field.onChange} />
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
                  <JalaliDatePicker value={field.value} onChange={field.onChange} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("common.type")}</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {CHECK_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {t(`checks.${type}`)}
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

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/checks")}
          >
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={createCheck.isPending}>
            {createCheck.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
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
            <SheetTitle>{t("checks.addTitle")}</SheetTitle>
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
          <Button variant="ghost" size="icon" onClick={() => navigate("/checks")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">{t("checks.addTitle")}</h1>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("checks.addTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {formContent}
        </CardContent>
      </Card>
    </motion.div>
  );
}
