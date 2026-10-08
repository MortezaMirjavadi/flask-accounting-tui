import { z } from "zod";

export const eventSchema = z.object({
  title: z.string().min(1, "validation.titleRequired"),
  description: z.string().optional().default(""),
  amount: z.coerce.number().min(0.01, "validation.amountPositive"),
  category_id: z.coerce.number().min(1, "validation.categoryRequired"),
  source_id: z.coerce.number().optional().nullable(),
  frequency: z.enum(["once", "daily", "weekly", "monthly", "yearly"], { required_error: "validation.typeRequired" }),
  repeat_interval: z.coerce.number().min(1, "validation.repeatIntervalMin").default(1),
  start_date: z.string().min(1, "validation.startDateRequired"),
  end_date: z.string().optional().nullable(),
  occurrence_limit: z.coerce.number().optional().nullable(),
});

export type EventFormInput = z.input<typeof eventSchema>;
export type EventFormData = z.infer<typeof eventSchema>;
