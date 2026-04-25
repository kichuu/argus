"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUIStore } from "@/store/ui";

export type NavItem = { id: string; code: string; label: string; href: string };
export type NavSection = { label: string; items: NavItem[] };

export const NAV_SECTIONS: NavSection[] = [
  {
    label: "Intel",
    items: [
      { id: "home", code: "F1", label: "Topic Launcher", href: "/" },
      { id: "world", code: "F2", label: "WorldView", href: "/world" },
      { id: "kg", code: "F3", label: "Knowledge Graph", href: "/kg" },
    ],
  },
  {
    label: "Council",
    items: [
      { id: "ops", code: "F4", label: "Agent Ops Theater", href: "/ops" },
    ],
  },
  {
    label: "Archive",
    items: [
      { id: "library", code: "F5", label: "Synthesis Library", href: "/library" },
      { id: "sources", code: "F6", label: "Source Monitor", href: "/sources" },
    ],
  },
  {
    label: "Live",
    items: [
      { id: "debate", code: "F7", label: "Debate Room", href: "/debate" },
    ],
  },
  {
    label: "System",
    items: [
      { id: "settings", code: "F8", label: "Settings", href: "/settings" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggle = useUIStore((s) => s.toggleSidebar);

  return (
    <div
      style={{
        width: collapsed ? 56 : 220,
        background: "var(--bg-1)",
        borderRight: "1px solid var(--line-2)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        transition: "width 0.16s ease-out",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "14px 14px 12px",
          borderBottom: "1px solid var(--line-2)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            background: "var(--amber)",
            color: "var(--bg-0)",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            flexShrink: 0,
          }}
        >
          ◉
        </div>
        {!collapsed && (
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1, minWidth: 0 }}>
            <span
              style={{
                fontWeight: 700,
                color: "var(--ink-0)",
                letterSpacing: "0.02em",
                fontSize: 13,
              }}
            >
              argus
            </span>
            <span className="tt-up" style={{ color: "var(--ink-3)", fontSize: 9 }}>
              WORLD AWARENESS v0.42
            </span>
          </div>
        )}
      </div>

      <div className="grow" style={{ overflowY: "auto", padding: "8px 0" }}>
        {NAV_SECTIONS.map((sec) => (
          <div key={sec.label} style={{ marginBottom: 12 }}>
            {!collapsed && (
              <div
                className="tt-up"
                style={{
                  color: "var(--ink-3)",
                  fontSize: 9,
                  padding: "4px 14px 6px",
                  letterSpacing: "0.16em",
                }}
              >
                {sec.label}
              </div>
            )}
            {sec.items.map((it) => {
              const active = pathname === it.href;
              return (
                <Link
                  key={it.id}
                  href={it.href}
                  style={{
                    padding: collapsed ? "6px 0" : "5px 14px",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    cursor: "pointer",
                    color: active ? "var(--amber)" : "var(--ink-1)",
                    background: active ? "var(--bg-3)" : "transparent",
                    borderLeft: active ? "2px solid var(--amber)" : "2px solid transparent",
                    fontSize: 12,
                    justifyContent: collapsed ? "center" : "flex-start",
                    textDecoration: "none",
                  }}
                  title={collapsed ? it.label : ""}
                >
                  <span
                    style={{
                      color: active ? "var(--amber)" : "var(--ink-3)",
                      fontSize: 9,
                      minWidth: collapsed ? "auto" : 22,
                      fontFeatureSettings: "'tnum'",
                    }}
                  >
                    {it.code}
                  </span>
                  {!collapsed && <span style={{ flex: 1 }}>{it.label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      <div
        onClick={toggle}
        style={{
          padding: "8px 14px",
          borderTop: "1px solid var(--line-2)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          cursor: "pointer",
          color: "var(--ink-2)",
          fontSize: 10,
        }}
      >
        <span>{collapsed ? "→" : "←"}</span>
        {!collapsed && <span className="tt-up">Collapse</span>}
      </div>
    </div>
  );
}
