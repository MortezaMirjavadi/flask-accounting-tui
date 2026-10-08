import { z } from "zod";

export const checkSchema = z.object({
  check_number: z.string().min(1, "validation.checkNumberRequired"),
  bank_name: z.string().min(1, "validation.bankNameRequired"),
  amount: z.coerce.number().min(0.01, "validation.amountPositive"),
  issue_date: z.string().min(1, "validation.issueDateRequired"),
  due_date: z.string().min(1, "validation.dueDateRequired"),
  type: z.enum(["issued", "received"], { required_error: "validation.typeRequired" }),
  wallet_id: z.coerce.number().optional().nullable(),
  source_id: z.coerce.number().optional().nullable(),
  category_id: z.coerce.number().min(1, "validation.categoryRequired"),
  description: z.string().optional().default(""),
});

export type CheckFormInput = z.input<typeof checkSchema>;
export type CheckFormData = z.infer<typeof checkSchema>;
