"use client";
import { create } from "zustand";

type UIState = {
  paletteOpen: boolean;
  notifsOpen: boolean;
  sidebarCollapsed: boolean;
  openPalette: () => void;
  closePalette: () => void;
  togglePalette: () => void;
  toggleNotifs: () => void;
  closeNotifs: () => void;
  toggleSidebar: () => void;
  closeAllOverlays: () => void;
};

export const useUIStore = create<UIState>((set) => ({
  paletteOpen: false,
  notifsOpen: false,
  sidebarCollapsed: false,
  openPalette: () => set({ paletteOpen: true }),
  closePalette: () => set({ paletteOpen: false }),
  togglePalette: () => set((s) => ({ paletteOpen: !s.paletteOpen })),
  toggleNotifs: () => set((s) => ({ notifsOpen: !s.notifsOpen })),
  closeNotifs: () => set({ notifsOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  closeAllOverlays: () => set({ paletteOpen: false, notifsOpen: false }),
}));
