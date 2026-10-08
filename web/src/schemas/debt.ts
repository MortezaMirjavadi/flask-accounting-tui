import { z } from "zod";

export const debtSchema = z.object({
  type: z.enum(["payable", "receivable"], { required_error: "validation.typeRequired" }),
  counterparty_name: z.string().min(1, "validation.counterpartyRequired"),
  counterparty_type: z.string().optional().default("person"),
  title: z.string().min(1, "validation.titleRequired"),
  description: z.string().optional().default(""),
  original_amount: z.coerce.number().min(0.01, "validation.amountPositive"),
  issue_date: z.string().min(1, "validation.issueDateRequired"),
  due_date: z.string().optional().nullable(),
  priority: z.string().optional().default("medium"),
  wallet_id: z.coerce.number().optional().nullable(),
  category_id: z.coerce.number().optional().nullable(),
  source_id: z.coerce.number().optional().nullable(),
  reference_type: z.string().optional().nullable(),
  reference_id: z.coerce.number().optional().nullable(),
  has_interest: z.boolean().optional().default(false),
  interest_type: z.string().optional().nullable(),
  interest_rate: z.coerce.number().optional().nullable(),
});

export const debtPaymentSchema = z.object({
  amount: z.coerce.number().min(0.01, "validation.amountPositive"),
  payment_date: z.string().min(1, "validation.paymentDateRequired"),
  payment_method: z.string().optional().default("cash"),
  wallet_id: z.coerce.number().optional().nullable(),
  category_id: z.coerce.number().optional().nullable(),
  source_id: z.coerce.number().optional().nullable(),
  note: z.string().optional().default(""),
});

export type DebtFormInput = z.input<typeof debtSchema>;
export type DebtFormData = z.infer<typeof debtSchema>;
export type DebtPaymentFormData = z.infer<typeof debtPaymentSchema>;
