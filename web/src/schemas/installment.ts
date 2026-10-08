import { z } from "zod";

export const installmentPlanSchema = z.object({
  title: z.string().min(1, "validation.titleRequired"),
  total_amount: z.coerce.number().min(0.01, "validation.totalAmountPositive"),
  installment_count: z.coerce.number().min(1, "validation.installmentCountMin"),
  installment_amount: z.coerce.number().min(0.01, "validation.installmentAmountPositive"),
  start_date: z.string().min(1, "validation.startDateRequired"),
  due_day_of_month: z.coerce.number().min(1, "validation.invalidDayOfMonth").max(31, "validation.invalidDayOfMonth"),
  category_id: z.coerce.number().min(1, "validation.categoryRequired"),
  wallet_id: z.coerce.number().optional().nullable(),
  source_id: z.coerce.number().optional().nullable(),
  status: z.string().optional().default("active"),
});

export const installmentPaymentSchema = z.object({
  installment_ids: z.array(z.number()).min(1, "validation.selectInstallments"),
  paid_date: z.string().min(1, "validation.paymentDateRequired"),
});

export type InstallmentPlanFormInput = z.input<typeof installmentPlanSchema>;
export type InstallmentPlanFormData = z.infer<typeof installmentPlanSchema>;
export type InstallmentPaymentFormData = z.infer<typeof installmentPaymentSchema>;
