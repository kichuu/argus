"use client";
import { useRouter } from "next/navigation";
import { useGlobalKeyboard } from "@/hooks/useKeyboard";
import { useUIStore } from "@/store/ui";

export function KeyboardShortcuts() {
  const router = useRouter();
  const openPalette = useUIStore((s) => s.openPalette);
  const closeAll = useUIStore((s) => s.closeAllOverlays);

  useGlobalKeyboard({
    onCommand: openPalette,
    onEscape: closeAll,
    onRoute: (path) => router.push(path),
  });

  return null;
}
