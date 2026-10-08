import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence, type PanInfo } from "framer-motion";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import {
  Wallet,
  ArrowRightLeft,
  PieChart,
  CalendarClock,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import type { TranslationKey } from "@/types/i18next";

const ONBOARDING_KEY = "onboarding_done";

const slides: {
  icon: typeof Wallet;
  titleKey: TranslationKey;
  descKey: TranslationKey;
  color: string;
}[] = [
  {
    icon: Wallet,
    titleKey: "intro.slide1.title",
    descKey: "intro.slide1.desc",
    color: "bg-blue-500/10 text-blue-500",
  },
  {
    icon: ArrowRightLeft,
    titleKey: "intro.slide2.title",
    descKey: "intro.slide2.desc",
    color: "bg-green-500/10 text-green-500",
  },
  {
    icon: PieChart,
    titleKey: "intro.slide3.title",
    descKey: "intro.slide3.desc",
    color: "bg-purple-500/10 text-purple-500",
  },
  {
    icon: CalendarClock,
    titleKey: "intro.slide4.title",
    descKey: "intro.slide4.desc",
    color: "bg-orange-500/10 text-orange-500",
  },
  {
    icon: Users,
    titleKey: "intro.slide5.title",
    descKey: "intro.slide5.desc",
    color: "bg-pink-500/10 text-pink-500",
  },
];

const DRAG_THRESHOLD = 50;

export default function IntroPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);
  const isRtl = i18n.dir() === "rtl";

  function finish() {
    localStorage.setItem(ONBOARDING_KEY, "true");
    navigate("/", { replace: true });
  }

  const next = useCallback(() => {
    if (current < slides.length - 1) {
      setCurrent((c) => c + 1);
    } else {
      finish();
    }
  }, [current]);

  const prev = useCallback(() => {
    if (current > 0) {
      setCurrent((c) => c - 1);
    }
  }, [current]);

  function handleDragEnd(_event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) {
    const { offset } = info;
    // In RTL, horizontal direction is flipped
    const dx = isRtl ? -offset.x : offset.x;
    if (dx < -DRAG_THRESHOLD) {
      next();
    } else if (dx > DRAG_THRESHOLD) {
      prev();
    }
  }

  const slide = slides[current];
  const Icon = slide.icon;

  return (
    <div className="flex h-svh flex-col items-center justify-between bg-background p-6">
      {/* Top bar */}
      <div className="flex w-full items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {current + 1} / {slides.length}
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <Button variant="ghost" size="sm" onClick={finish}>
            {t("intro.skip")}
          </Button>
        </div>
      </div>

      {/* Slide content — draggable */}
      <div className="flex flex-1 items-center justify-center overflow-hidden">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={current}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.3 }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.2}
            onDragEnd={handleDragEnd}
            className="flex cursor-grab flex-col items-center gap-6 text-center active:cursor-grabbing"
          >
            <div className={`flex h-24 w-24 items-center justify-center rounded-3xl ${slide.color}`}>
              <Icon className="h-12 w-12" />
            </div>
            <div className="space-y-3">
              <h2 className="text-2xl font-bold">{t(slide.titleKey)}</h2>
              <p className="max-w-md text-muted-foreground">{t(slide.descKey)}</p>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Bottom controls: prev (left) — dots (center) — next (right) */}
      <div className="flex w-full items-center justify-between">
        <Button
          variant="ghost"
          size="icon"
          onClick={prev}
          disabled={current === 0}
          className="h-10 w-10"
        >
          <ChevronLeft className="h-5 w-5" />
        </Button>

        {/* Dots */}
        <div className="flex items-center gap-2">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              className={`h-2 rounded-full transition-all ${
                i === current ? "w-6 bg-primary" : "w-2 bg-muted-foreground/30"
              }`}
            />
          ))}
        </div>

        <Button onClick={next} className="h-10 px-6">
          {current === slides.length - 1 ? t("intro.start") : t("intro.next")}
          <ChevronRight className="ms-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
