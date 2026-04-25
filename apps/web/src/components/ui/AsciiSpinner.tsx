"use client";
import { useEffect, useState } from "react";

const DEFAULT_CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export function AsciiSpinner({
  chars = DEFAULT_CHARS,
  speed = 80,
  color = "var(--amber)",
}: {
  chars?: string[];
  speed?: number;
  color?: string;
}) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((x) => (x + 1) % chars.length), speed);
    return () => clearInterval(id);
  }, [chars.length, speed]);
  return <span style={{ color }}>{chars[i]}</span>;
}
