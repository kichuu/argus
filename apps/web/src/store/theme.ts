"use client";
import { create } from "zustand";

export type ThemeMode = "dark" | "light";
export type LightVariant = "paper" | "cool" | "ledger";

type ThemeState = {
  theme: ThemeMode;
  lightVariant: LightVariant;
  setTheme: (t: ThemeMode) => void;
  setLightVariant: (v: LightVariant) => void;
  toggle: () => void;
};

export const useThemeStore = create<ThemeState>((set) => ({
  theme: "dark",
  lightVariant: "paper",
  setTheme: (theme) => set({ theme }),
  setLightVariant: (lightVariant) => set({ lightVariant }),
  toggle: () => set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
}));
