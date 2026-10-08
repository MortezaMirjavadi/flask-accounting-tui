import { z } from "zod";

export const transactionItemSchema = z.object({
  name: z.string().min(1, "validation.itemNameRequired"),
  quantity: z.coerce.number().min(0.01, "validation.quantityPositive"),
  unit: z.string().optional().default(""),
  unit_price: z.coerce.number().min(0, "validation.amountNonNegative"),
  total_price: z.coerce.number().min(0, "validation.amountNonNegative"),
  notes: z.string().optional().default(""),
});

export const transactionSchema = z.object({
  date: z.string().min(1, "validation.dateRequired"),
  amount: z.coerce.number().min(0.01, "validation.amountPositive"),
  category_id: z.coerce.number().min(1, "validation.categoryRequired"),
  source_id: z.coerce.number().min(1, "validation.accountRequired"),
  account_id: z.number().optional(),
  wallet_id: z.number().optional(),
  is_private: z.boolean().optional().default(false),
  description: z.string().optional().default(""),
  items: z.array(transactionItemSchema).optional().default([]),
});

export const transferSchema = z.object({
  from_account_id: z.coerce.number().min(1, "validation.fromAccountRequired"),
  to_account_id: z.coerce.number().min(1, "validation.toAccountRequired"),
  amount: z.coerce.number().min(0.01, "validation.amountPositive"),
  date: z.string().min(1, "validation.dateRequired"),
  notes: z.string().optional().default(""),
});

export type TransactionFormData = z.infer<typeof transactionSchema>;
export type TransactionItemFormData = z.infer<typeof transactionItemSchema>;
export type TransferFormData = z.infer<typeof transferSchema>;
