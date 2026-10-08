import { z } from "zod";

export const budgetPeriodSchema = z.object({
  year: z.coerce.number().min(1300, "validation.invalidYear").max(1500, "validation.invalidYear"),
  month: z.coerce.number().min(1, "validation.invalidMonth").max(12, "validation.invalidMonth"),
});

export const budgetItemSchema = z.object({
  category_id: z.coerce.number().min(1, "validation.categoryRequired"),
  planned_amount: z.coerce.number().min(0, "validation.amountNonNegative"),
  notes: z.string().optional().default(""),
});

export type BudgetPeriodFormData = z.infer<typeof budgetPeriodSchema>;
export type BudgetItemFormInput = z.input<typeof budgetItemSchema>;
export type BudgetItemFormData = z.infer<typeof budgetItemSchema>;
