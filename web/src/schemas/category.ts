import { z } from "zod";

export const categorySchema = z.object({
  name: z.string().min(1, "نام دسته‌بندی الزامی است"),
  type: z.enum(["income", "cost"], { required_error: "نوع الزامی است" }),
});

export type CategoryFormData = z.infer<typeof categorySchema>;
