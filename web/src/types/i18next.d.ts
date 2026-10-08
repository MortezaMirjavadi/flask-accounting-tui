import type en from "../i18n/locales/en/translation.json";
import type fa from "../i18n/locales/fa/translation.json";

/**
 * Feeds the shape of the translation files into i18next's TypeScript types,
 * so `t("...")` gets IntelliSense autocomplete and typos become type errors.
 *
 * The en and fa resource types are intersected so keys that only exist in one
 * locale still autocomplete (missing translations fall back at runtime).
 */
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    resources: {
      translation: typeof en & typeof fa;
    };
  }
}

/** Flattens a nested resource object into dot-separated key unions (leaf keys only). */
type FlattenKeys<T> = T extends object
  ? {
      [K in keyof T & string]: T[K] extends object
        ? `${K}.${FlattenKeys<T[K]>}`
        : `${K}`;
    }[keyof T & string]
  : never;

/** Every valid translation key, e.g. `"common.save"` | `"validation.required"` | ... */
export type TranslationKey = FlattenKeys<typeof en & typeof fa>;
