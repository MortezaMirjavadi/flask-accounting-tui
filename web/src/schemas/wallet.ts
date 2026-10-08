import { z } from "zod";

export const walletSchema = z.object({
  name: z.string().min(1, "validation.nameRequired"),
  currency: z.enum(["IRR", "USD", "EUR", "GBP", "AED"], { required_error: "validation.currencyRequired" }).default("IRR"),
  wallet_type: z.enum(["personal", "shared"], { required_error: "validation.typeRequired" }).default("personal"),
  variant: z.enum(["family", "team", "travel", "business", "savings"]).optional().nullable(),
  icon: z.string().optional(),
  description: z.string().optional(),
});

export type WalletFormInput = z.input<typeof walletSchema>;
export type WalletFormData = z.infer<typeof walletSchema>;

export const accountSchema = z.object({
  name: z.string().min(1, "validation.nameRequired"),
  account_type: z.enum(["cash", "bank", "card", "savings", "wallet", "other"], { required_error: "validation.typeRequired" }).default("cash"),
  bank_type: z.string().optional().default("cash"),
  amount: z.coerce.number().min(0, "validation.amountNonNegative").optional().default(0),
  icon: z.string().optional(),
  description: z.string().optional(),
  sort_order: z.number().optional().default(0),
});

export type AccountFormInput = z.input<typeof accountSchema>;
export type AccountFormData = z.infer<typeof accountSchema>;

export const exchangeRateSchema = z.object({
  from_currency: z.string().min(3, "validation.currencyCode").max(3, "validation.currencyCode"),
  to_currency: z.string().min(3, "validation.currencyCode").max(3, "validation.currencyCode"),
  rate: z.coerce.number().positive("validation.ratePositive"),
});

export type ExchangeRateFormData = z.infer<typeof exchangeRateSchema>;
