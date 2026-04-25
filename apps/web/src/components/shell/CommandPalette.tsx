"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type SearchHit, type SearchKind } from "@/lib/api";
import { useUIStore } from "@/store/ui";

type Section = { kind: SearchKind; label: string; hits: SearchHit[] };

const KIND_LABELS: Record<SearchKind, string> = {
  claims: "Claims",
  sources: "Sources",
  entities: "Entities",
  discussions: "Discussions",
};

const ALL_KINDS: SearchKind[] = ["claims", "sources", "entities", "discussions"];

export function CommandPalette() {
  const router = useRouter();
  const open = useUIStore((s) => s.paletteOpen);
  const close = useUIStore((s) => s.closePalette);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset on open / close.
  useEffect(() => {
    if (open) {
      setQ("");
      setDebouncedQ("");
      setActiveIdx(0);
      // focus on next tick so the input is mounted
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  // 200ms debounce for the query string.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 200);
    return () => clearTimeout(t);
  }, [q]);

  const ready = debouncedQ.length >= 2;

  const search = useQuery({
    queryKey: ["search", debouncedQ],
    queryFn: () => api.search(debouncedQ, { kinds: ALL_KINDS, limit: 5 }),
    enabled: open && ready,
    staleTime: 5_000,
    retry: 0,
  });

  // Flatten sections + a flat list for keyboard navigation.
  const sections: Section[] = useMemo(() => {
    const r = search.data?.results;
    if (!r) return [];
    return ALL_KINDS.map((k) => ({
      kind: k,
      label: KIND_LABELS[k],
      hits: r[k] ?? [],
    })).filter((s) => s.hits.length > 0);
  }, [search.data]);

  const flatHits: SearchHit[] = useMemo(
    () => sections.flatMap((s) => s.hits),
    [sections],
  );

  // Reset selection when results change.
  useEffect(() => {
    setActiveIdx(0);
  }, [debouncedQ, search.data]);

  if (!open) return null;

  const onPick = (hit: SearchHit) => {
    router.push(hit.href);
    close();
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      close();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, Math.max(flatHits.length - 1, 0)));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === "Enter") {
      const target = flatHits[activeIdx];
      if (target) onPick(target);
      return;
    }
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
            placeholder="Search claims, sources, entities, debates"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--ink-0)",
              fontFamily: "inherit",
              fontSize: 13,
            }}
            onKeyDown={onKeyDown}
          />
          <span className="muted tt-up" style={{ fontSize: 9 }}>
            ESC
          </span>
        </div>

        <div style={{ maxHeight: 420, overflowY: "auto" }}>
          {!ready && (
            <div
              style={{
                padding: 20,
                color: "var(--ink-3)",
                fontSize: 11,
                textAlign: "center",
              }}
            >
              Type to search across claims, sources, entities, debates.
            </div>
          )}

          {ready && search.isLoading && (
            <Skeleton rows={5} rowHeight={14} gap={10} />
          )}

          {ready && search.isError && (
            <EmptyState
              title="Search failed"
              hint={`Could not reach the API. Tried "${debouncedQ}".`}
              style={{ margin: 16 }}
            />
          )}

          {ready &&
            search.isSuccess &&
            sections.length === 0 && (
              <EmptyState
                title="No matches"
                hint={`Tried "${debouncedQ}" across all kinds.`}
                style={{ margin: 16 }}
              />
            )}

          {ready && search.isSuccess && sections.length > 0 && (
            <div>
              {(() => {
                let runningIdx = 0;
                return sections.map((section) => (
                  <div key={section.kind}>
                    <div
                      className="tt-up"
                      style={{
                        padding: "8px 14px 4px",
                        fontSize: 9,
                        color: "var(--ink-3)",
                        letterSpacing: "0.12em",
                        background: "var(--bg-1)",
                        borderTop: "1px solid var(--line-1)",
                      }}
                    >
                      {section.label}
                    </div>
                    {section.hits.map((hit) => {
                      const i = runningIdx++;
                      const active = i === activeIdx;
                      return (
                        <div
                          key={`${section.kind}:${hit.id}`}
                          onMouseEnter={() => setActiveIdx(i)}
                          onClick={() => onPick(hit)}
                          style={{
                            padding: "8px 14px",
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                            fontSize: 12,
                            cursor: "pointer",
                            borderBottom: "1px solid var(--line-1)",
                            background: active ? "var(--bg-3)" : "transparent",
                          }}
                        >
                          <span
                            className="tt-up"
                            style={{
                              color: "var(--amber)",
                              fontSize: 9,
                              minWidth: 60,
                            }}
                          >
                            {section.kind}
                          </span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div
                              style={{
                                color: "var(--ink-0)",
                                whiteSpace: "nowrap",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                              }}
                            >
                              {hit.label}
                            </div>
                            {hit.snippet && (
                              <div
                                style={{
                                  fontSize: 10,
                                  color: "var(--ink-3)",
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                }}
                              >
                                {hit.snippet}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ));
              })()}
            </div>
          )}
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
          {ready && search.isSuccess && (
            <span style={{ marginLeft: "auto" }}>
              {search.data?.total ?? 0} HITS
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
