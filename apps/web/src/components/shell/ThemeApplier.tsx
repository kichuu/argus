"use client";
import { useEffect } from "react";
import { useThemeStore } from "@/store/theme";

export function ThemeApplier() {
  const theme = useThemeStore((s) => s.theme);
  const variant = useThemeStore((s) => s.lightVariant);
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-light-variant", variant);
  }, [theme, variant]);
  return null;
}
