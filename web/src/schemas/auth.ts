import { z } from "zod";

export const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  display_name: z.string().min(1, "Display name is required"),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
});

export const twoFaSchema = z.object({
  code: z.string().length(6, "Code must be 6 digits"),
});

export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type TwoFaFormData = z.infer<typeof twoFaSchema>;
