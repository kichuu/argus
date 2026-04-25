"use client";
import { useEffect } from "react";

const FN_ROUTE: Record<string, string> = {
  F1: "/",
  F2: "/world",
  F3: "/kg",
  F4: "/ops",
  F5: "/personas",
  F6: "/debate",
  F7: "/synthesis",
  F8: "/library",
  F9: "/replay",
  F10: "/compare",
  F11: "/sources",
  F12: "/obs",
};

type Handlers = {
  onCommand: () => void;
  onEscape: () => void;
  onRoute: (path: string) => void;
};

export function useGlobalKeyboard({ onCommand, onEscape, onRoute }: Handlers): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onCommand();
        return;
      }
      if (e.key === "Escape") {
        onEscape();
        return;
      }
      const route = FN_ROUTE[e.key];
      if (route) {
        e.preventDefault();
        onRoute(route);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCommand, onEscape, onRoute]);
}
