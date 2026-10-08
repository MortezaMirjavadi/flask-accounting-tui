import { z } from "zod";

export const contactSchema = z.object({
  name: z.string().min(1, "validation.nameRequired"),
  phone: z.string().optional().default(""),
  email: z.string().email("validation.invalidEmail").optional().or(z.literal("")),
  address: z.string().optional().default(""),
  notes: z.string().optional().default(""),
});

export const tagSchema = z.object({
  name: z.string().min(1, "validation.tagNameRequired"),
  color: z.string().optional().default("#3b82f6"),
});

export const labelSchema = z.object({
  name: z.string().min(1, "validation.labelNameRequired"),
  color: z.string().optional().default("#3b82f6"),
});

export type ContactFormInput = z.input<typeof contactSchema>;
export type ContactFormData = z.infer<typeof contactSchema>;
export type TagFormInput = z.input<typeof tagSchema>;
export type TagFormData = z.infer<typeof tagSchema>;
export type LabelFormInput = z.input<typeof labelSchema>;
export type LabelFormData = z.infer<typeof labelSchema>;
