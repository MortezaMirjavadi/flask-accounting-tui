import { z } from "zod";

export const walletSchema = z.object({
  name: z.string().min(1),
  currency: z.enum(["IRR", "USD", "EUR", "GBP", "AED"]).default("IRR"),
  wallet_type: z.enum(["personal", "shared"]).default("personal"),
  variant: z.enum(["family", "team", "travel", "business", "savings"]).optional().nullable(),
  icon: z.string().optional(),
  description: z.string().optional(),
});

export type WalletFormData = z.infer<typeof walletSchema>;

export const accountSchema = z.object({
  name: z.string().min(1),
  account_type: z.enum(["cash", "bank", "card", "savings", "wallet", "other"]).default("cash"),
  bank_type: z.string().optional().default("cash"),
  amount: z.coerce.number().min(0).optional().default(0),
  icon: z.string().optional(),
  description: z.string().optional(),
  sort_order: z.number().optional().default(0),
});

export type AccountFormData = z.infer<typeof accountSchema>;

export const exchangeRateSchema = z.object({
  from_currency: z.string().min(3).max(3),
  to_currency: z.string().min(3).max(3),
  rate: z.coerce.number().positive(),
});

export type ExchangeRateFormData = z.infer<typeof exchangeRateSchema>;
