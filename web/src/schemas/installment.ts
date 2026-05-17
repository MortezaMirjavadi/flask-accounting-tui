import { z } from "zod";

export const installmentPlanSchema = z.object({
  title: z.string().min(1, "عنوان الزامی است"),
  total_amount: z.coerce.number().min(0.01, "مبلغ کل باید مثبت باشد"),
  installment_count: z.coerce.number().min(1, "حداقل یک قسط لازم است"),
  installment_amount: z.coerce.number().min(0.01, "مبلغ قسط باید مثبت باشد"),
  start_date: z.string().min(1, "تاریخ شروع الزامی است"),
  due_day_of_month: z.coerce.number().min(1).max(31),
  category_id: z.coerce.number().optional().nullable(),
  source_id: z.coerce.number().optional().nullable(),
  status: z.string().optional().default("active"),
});

export const installmentPaymentSchema = z.object({
  installment_ids: z.array(z.number()).min(1, "حداقل یک قسط انتخاب کنید"),
  paid_date: z.string().min(1, "تاریخ پرداخت الزامی است"),
});

export type InstallmentPlanFormData = z.infer<typeof installmentPlanSchema>;
export type InstallmentPaymentFormData = z.infer<typeof installmentPaymentSchema>;
