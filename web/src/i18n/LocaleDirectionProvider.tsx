import { useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { DirectionProvider } from "@radix-ui/react-direction";
import { useDirection } from "./hooks";

/**
 * Provides the reading direction to all Radix primitives (Select, DropdownMenu, Popover, …)
 * based on the active locale, and keeps <html dir/lang> in sync so portal content and the
 * Tailwind `rtl:`/`ltr:` variants follow the locale as well.
 */
export function LocaleDirectionProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const direction = useDirection();

  useEffect(() => {
    document.documentElement.lang = i18n.language;
    document.documentElement.dir = direction;
  }, [i18n.language, direction]);

  return <DirectionProvider dir={direction}>{children}</DirectionProvider>;
}
