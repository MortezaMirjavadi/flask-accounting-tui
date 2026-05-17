import { z } from "zod";

export const debtSchema = z.object({
  type: z.enum(["payable", "receivable"], { required_error: "نوع الزامی است" }),
  counterparty_name: z.string().min(1, "نام طرف حساب الزامی است"),
  counterparty_type: z.string().optional().default("person"),
  title: z.string().min(1, "عنوان الزامی است"),
  description: z.string().optional().default(""),
  original_amount: z.coerce.number().min(0.01, "مبلغ باید مثبت باشد"),
  issue_date: z.string().min(1, "تاریخ صدور الزامی است"),
  due_date: z.string().optional().nullable(),
  priority: z.string().optional().default("medium"),
  source_id: z.coerce.number().optional().nullable(),
  reference_type: z.string().optional().nullable(),
  reference_id: z.coerce.number().optional().nullable(),
  has_interest: z.boolean().optional().default(false),
  interest_type: z.string().optional().nullable(),
  interest_rate: z.coerce.number().optional().nullable(),
});

export const debtPaymentSchema = z.object({
  amount: z.coerce.number().min(0.01, "مبلغ باید مثبت باشد"),
  payment_date: z.string().min(1, "تاریخ پرداخت الزامی است"),
  payment_method: z.string().optional().default("cash"),
  source_id: z.coerce.number().optional().nullable(),
  note: z.string().optional().default(""),
});

export type DebtFormData = z.infer<typeof debtSchema>;
export type DebtPaymentFormData = z.infer<typeof debtPaymentSchema>;
