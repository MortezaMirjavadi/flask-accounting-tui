import { z } from "zod";

export const eventSchema = z.object({
  title: z.string().min(1, "عنوان الزامی است"),
  description: z.string().optional().default(""),
  amount: z.coerce.number().min(0.01, "مبلغ باید مثبت باشد"),
  category_id: z.coerce.number().min(1, "دسته‌بندی الزامی است"),
  source_id: z.coerce.number().optional().nullable(),
  frequency: z.enum(["once", "daily", "weekly", "monthly", "yearly"]),
  repeat_interval: z.coerce.number().min(1).default(1),
  start_date: z.string().min(1, "تاریخ شروع الزامی است"),
  end_date: z.string().optional().nullable(),
  occurrence_limit: z.coerce.number().optional().nullable(),
});

export type EventFormInput = z.input<typeof eventSchema>;
export type EventFormData = z.infer<typeof eventSchema>;
