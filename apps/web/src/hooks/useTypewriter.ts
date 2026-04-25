"use client";
import { useEffect, useState } from "react";

export function useTypewriter(text: string, enabled: boolean, speed = 8, onDone?: () => void): string {
  const [out, setOut] = useState(enabled ? "" : text);
  useEffect(() => {
    if (!enabled) {
      setOut(text);
      return;
    }
    setOut("");
    let i = 0;
    const id = setInterval(() => {
      i += Math.max(1, Math.floor(text.length / 200));
      if (i >= text.length) {
        setOut(text);
        clearInterval(id);
        onDone?.();
      } else {
        setOut(text.slice(0, i));
      }
    }, speed);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, enabled]);
  return out;
}
