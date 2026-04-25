"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ARGUS_DATA } from "@/mock/data";
import { useUIStore } from "@/store/ui";
import { NAV_SECTIONS } from "./Sidebar";

type Item = {
  kind: "nav" | "debate" | "persona" | "entity";
  id: string;
  label: string;
  code: string;
  group: string;
  href?: string;
};

export function CommandPalette() {
  const router = useRouter();
  const open = useUIStore((s) => s.paletteOpen);
  const close = useUIStore((s) => s.closePalette);
  const [q, setQ] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
    if (open) setQ("");
  }, [open]);

  const allItems: Item[] = useMemo(() => {
    const navs: Item[] = NAV_SECTIONS.flatMap((s) =>
      s.items.map((i) => ({
        kind: "nav",
        id: i.id,
        label: i.label,
        code: i.code,
        group: s.label,
        href: i.href,
      })),
    );
    const debates: Item[] = ARGUS_DATA.RECENT.map((d) => ({
      kind: "debate",
      id: d.id,
      label: d.title,
      code: d.id,
      group: "Debates",
    }));
    const personas: Item[] = ARGUS_DATA.PERSONAS.map((p) => ({
      kind: "persona",
      id: p.id,
      label: `${p.name} — ${p.role}`,
      code: p.flag,
      group: "Personas",
    }));
    const ents: Item[] = ARGUS_DATA.KG_ENTITIES.map((e) => ({
      kind: "entity",
      id: e.id,
      label: e.label,
      code: e.type,
      group: "Entities",
    }));
    return [...navs, ...debates, ...personas, ...ents];
  }, []);

  const filtered = useMemo(() => {
    if (!q) return allItems.slice(0, 12);
    const ql = q.toLowerCase();
    return allItems
      .filter((i) => i.label.toLowerCase().includes(ql) || i.code.toLowerCase().includes(ql))
      .slice(0, 14);
  }, [q, allItems]);

  if (!open) return null;

  const onPick = (it: Item) => {
    if (it.kind === "nav" && it.href) router.push(it.href);
    close();
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: 100,
        zIndex: 9999,
      }}
      onClick={close}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 600,
          background: "var(--bg-2)",
          border: "1px solid var(--line-3)",
          boxShadow: "0 24px 60px rgba(0,0,0,0.6)",
        }}
      >
        <div
          style={{
            padding: "12px 14px",
            borderBottom: "1px solid var(--line-2)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span style={{ color: "var(--amber)", fontSize: 14 }}>⌘</span>
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Type to search — entities, debates, personas, screens"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--ink-0)",
              fontFamily: "inherit",
              fontSize: 13,
            }}
            onKeyDown={(e) => {
              if (e.key === "Escape") close();
              if (e.key === "Enter" && filtered[0]) onPick(filtered[0]);
            }}
          />
          <span className="muted tt-up" style={{ fontSize: 9 }}>
            ESC
          </span>
        </div>
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {filtered.length === 0 && (
            <div
              style={{
                padding: 20,
                color: "var(--ink-3)",
                fontSize: 11,
                textAlign: "center",
              }}
            >
              No matches
            </div>
          )}
          {filtered.map((it, i) => (
            <div
              key={it.kind + it.id}
              onClick={() => onPick(it)}
              style={{
                padding: "8px 14px",
                display: "flex",
                alignItems: "center",
                gap: 10,
                fontSize: 12,
                cursor: "pointer",
                borderBottom: "1px solid var(--line-1)",
                background: i === 0 ? "var(--bg-3)" : "transparent",
              }}
            >
              <span
                className="tt-up"
                style={{ color: "var(--amber)", fontSize: 9, minWidth: 60 }}
              >
                {it.kind}
              </span>
              <span style={{ flex: 1, color: "var(--ink-0)" }}>{it.label}</span>
              <span className="muted" style={{ fontSize: 10 }}>
                {it.code}
              </span>
            </div>
          ))}
        </div>
        <div
          style={{
            padding: "6px 14px",
            borderTop: "1px solid var(--line-2)",
            display: "flex",
            gap: 14,
            fontSize: 9,
            color: "var(--ink-3)",
          }}
          className="tt-up"
        >
          <span>↵ OPEN</span>
          <span>↑↓ NAVIGATE</span>
          <span>ESC CLOSE</span>
        </div>
      </div>
    </div>
  );
}
