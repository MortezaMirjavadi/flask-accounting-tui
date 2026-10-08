import { z } from "zod";

export const categorySchema = z.object({
  name: z.string().min(1, "validation.categoryNameRequired"),
  type: z.enum(["income", "cost"], { required_error: "validation.typeRequired" }),
  parent_id: z.number().nullable().optional(),
});

export type CategoryFormData = z.infer<typeof categorySchema>;
