import { z } from "zod";

export const transactionItemSchema = z.object({
  name: z.string().min(1, "نام قلم الزامی است"),
  quantity: z.coerce.number().min(0.01, "تعداد باید مثبت باشد"),
  unit: z.string().optional().default(""),
  unit_price: z.coerce.number().min(0, "قیمت واحد نمی‌تواند منفی باشد"),
  total_price: z.coerce.number().min(0, "قیمت کل نمی‌تواند منفی باشد"),
  notes: z.string().optional().default(""),
});

export const transactionSchema = z.object({
  date: z.string().min(1, "تاریخ الزامی است"),
  amount: z.coerce.number().min(0.01, "مبلغ باید مثبت باشد"),
  category_id: z.coerce.number().min(1, "دسته‌بندی الزامی است"),
  source_id: z.coerce.number().min(1, "حساب الزامی است"),
  account_id: z.number().optional(),
  wallet_id: z.number().optional(),
  is_private: z.boolean().optional().default(false),
  description: z.string().optional().default(""),
  items: z.array(transactionItemSchema).optional().default([]),
});

export const transferSchema = z.object({
  from_account_id: z.coerce.number().min(1, "حساب مبدا الزامی است"),
  to_account_id: z.coerce.number().min(1, "حساب مقصد الزامی است"),
  amount: z.coerce.number().min(0.01, "مبلغ باید مثبت باشد"),
  date: z.string().min(1, "تاریخ الزامی است"),
  notes: z.string().optional().default(""),
});

export type TransactionFormData = z.infer<typeof transactionSchema>;
export type TransactionItemFormData = z.infer<typeof transactionItemSchema>;
export type TransferFormData = z.infer<typeof transferSchema>;
