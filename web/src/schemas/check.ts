import { z } from "zod";

export const checkSchema = z.object({
  check_number: z.string().min(1, "شماره چک الزامی است"),
  bank_name: z.string().min(1, "نام بانک الزامی است"),
  amount: z.coerce.number().min(0.01, "مبلغ باید مثبت باشد"),
  issue_date: z.string().min(1, "تاریخ صدور الزامی است"),
  due_date: z.string().min(1, "تاریخ سررسید الزامی است"),
  type: z.enum(["issued", "received"], { required_error: "نوع الزامی است" }),
  source_id: z.coerce.number().optional().nullable(),
  category_id: z.coerce.number().optional().nullable(),
  description: z.string().optional().default(""),
});

export type CheckFormData = z.infer<typeof checkSchema>;
