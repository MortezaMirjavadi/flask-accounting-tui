import { z } from "zod";

export const sourceSchema = z.object({
  name: z.string().min(1, { message: "validation.accountNameRequired" }),
  amount: z.coerce.number().min(0, "validation.amountNonNegative"),
  bank_type: z.string().optional().default("cash"),
});

export type SourceFormInput = z.input<typeof sourceSchema>;
export type SourceFormData = z.infer<typeof sourceSchema>;
