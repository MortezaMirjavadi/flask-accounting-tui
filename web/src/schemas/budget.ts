import { z } from "zod";

export const budgetPeriodSchema = z.object({
  year: z.coerce.number().min(1300, "سال نامعتبر است").max(1500, "سال نامعتبر است"),
  month: z.coerce.number().min(1, "ماه باید بین ۱ تا ۱۲ باشد").max(12, "ماه باید بین ۱ تا ۱۲ باشد"),
});

export const budgetItemSchema = z.object({
  category_id: z.coerce.number().min(1, "دسته‌بندی الزامی است"),
  planned_amount: z.coerce.number().min(0, "مبلغ نمی‌تواند منفی باشد"),
  notes: z.string().optional().default(""),
});

export type BudgetPeriodFormData = z.infer<typeof budgetPeriodSchema>;
export type BudgetItemFormData = z.infer<typeof budgetItemSchema>;
