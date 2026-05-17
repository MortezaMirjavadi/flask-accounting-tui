import { z } from "zod";

export const sourceSchema = z.object({
  name: z.string().min(1, { message: "نام حساب الزامی است" }),
  amount: z.coerce.number().min(0, "مبلغ نمی‌تواند منفی باشد"),
  bank_type: z.string().optional().default("cash"),
});

export type SourceFormData = z.infer<typeof sourceSchema>;
