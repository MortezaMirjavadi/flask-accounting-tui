import { z } from "zod";

export const contactSchema = z.object({
  name: z.string().min(1, "نام الزامی است"),
  phone: z.string().optional().default(""),
  email: z.string().email("ایمیل نامعتبر است").optional().or(z.literal("")),
  address: z.string().optional().default(""),
  notes: z.string().optional().default(""),
});

export const tagSchema = z.object({
  name: z.string().min(1, "نام برچسب الزامی است"),
  color: z.string().optional().default("#3b82f6"),
});

export const labelSchema = z.object({
  name: z.string().min(1, "نام برچسب الزامی است"),
  color: z.string().optional().default("#3b82f6"),
});

export type ContactFormData = z.infer<typeof contactSchema>;
export type TagFormData = z.infer<typeof tagSchema>;
export type LabelFormData = z.infer<typeof labelSchema>;
