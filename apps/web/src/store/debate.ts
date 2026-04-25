"use client";
import { create } from "zustand";

type DebateState = {
  idx: number;
  topic: string;
  paused: boolean;
  speed: number;
  setIdx: (idx: number) => void;
  advance: (max: number) => void;
  stepBack: () => void;
  reset: () => void;
  skipToEnd: (max: number) => void;
  setTopic: (topic: string) => void;
  setPaused: (paused: boolean) => void;
  setSpeed: (speed: number) => void;
};

export const useDebateStore = create<DebateState>((set) => ({
  idx: 0,
  topic: "",
  paused: false,
  speed: 1,
  setIdx: (idx) => set({ idx }),
  advance: (max) => set((s) => ({ idx: Math.min(max, s.idx + 1) })),
  stepBack: () => set((s) => ({ idx: Math.max(0, s.idx - 1) })),
  reset: () => set({ idx: 0 }),
  skipToEnd: (max) => set({ idx: max }),
  setTopic: (topic) => set({ topic, idx: 0 }),
  setPaused: (paused) => set({ paused }),
  setSpeed: (speed) => set({ speed }),
}));
