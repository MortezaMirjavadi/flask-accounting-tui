import { z } from "zod";

export const loginSchema = z.object({
  username: z.string().min(1, "validation.usernameRequired"),
  password: z.string().min(1, "validation.passwordRequired"),
});

export const registerSchema = z.object({
  username: z.string().min(3, "validation.usernameMin"),
  password: z.string().min(6, "validation.passwordMin"),
  display_name: z.string().min(1, "validation.displayNameRequired"),
  email: z
    .string()
    .email("validation.invalidEmail")
    .optional()
    .or(z.literal("")),
});

export const twoFaSchema = z.object({
  code: z.string().length(6, "validation.codeLength"),
});

export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type TwoFaFormData = z.infer<typeof twoFaSchema>;
