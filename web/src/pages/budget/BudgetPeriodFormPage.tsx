import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import {
  useBudgetPeriod,
  useCreateBudgetPeriod,
  useUpdateBudgetPeriod,
} from "@/hooks/budget";
import {
  budgetPeriodSchema,
  type BudgetPeriodFormData,
} from "@/schemas/budget";
import { PERSIAN_MONTHS } from "@/lib/constants";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
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

// Jalali years range
const currentJalaliYear = new Date().toLocaleDateString("fa-IR-u-nu-latn", {
  calendar: "persian",
  year: "numeric",
});

const yearOptions = Array.from(
  { length: 11 },
  (_, i) => Number(currentJalaliYear) - 5 + i,
);

export default function BudgetPeriodFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const isMobile = useIsMobile();

  const { data: period, isLoading: periodLoading } = useBudgetPeriod(
    Number(id) || 0,
  );
  const createMutation = useCreateBudgetPeriod();
  const updateMutation = useUpdateBudgetPeriod();

  const form = useForm<BudgetPeriodFormData>({
    resolver: zodResolver(budgetPeriodSchema),
    defaultValues: {
      year: Number(currentJalaliYear),
      month: 1,
    },
  });

  useEffect(() => {
    if (isEdit && period) {
      form.reset({ year: period.year, month: period.month });
    }
  }, [isEdit, period, form]);

  async function onSubmit(data: BudgetPeriodFormData) {
    try {
      if (isEdit) {
        await updateMutation.mutateAsync({ id: Number(id), data });
        toast.success(t("common.success"));
      } else {
        await createMutation.mutateAsync(data);
        toast.success(t("common.success"));
      }
      navigate("/budget/periods");
    } catch {
      toast.error(t("common.error"));
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  if (isEdit && periodLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const formContent = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="year"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("budget.year")}</FormLabel>
              <Select
                onValueChange={(val) => field.onChange(Number(val))}
                value={String(field.value)}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {yearOptions.map((y) => (
                    <SelectItem key={y} value={String(y)}>
                      {y}
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
          name="month"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("budget.month")}</FormLabel>
              <Select
                onValueChange={(val) => field.onChange(Number(val))}
                value={String(field.value)}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {PERSIAN_MONTHS.map((m, i) => (
                    <SelectItem key={i + 1} value={String(i + 1)}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex items-center justify-end gap-3 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(-1)}
          >
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending && (
              <Loader2 className="me-2 h-4 w-4 animate-spin" />
            )}
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
            <SheetTitle>
              {isEdit ? t("budget.editPeriod") : t("budget.addPeriod")}
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
      className="space-y-6"
    >
      <h1 className="text-2xl font-bold">
        {isEdit ? t("budget.editPeriod") : t("budget.addPeriod")}
      </h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            {isEdit ? t("budget.editPeriod") : t("budget.addPeriod")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {formContent}
        </CardContent>
      </Card>
    </motion.div>
  );
}
