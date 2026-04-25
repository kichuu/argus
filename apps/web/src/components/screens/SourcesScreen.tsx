"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { KV } from "@/components/ui/KV";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type Source } from "@/lib/api";

const PAGE_SIZE = 50;

const TIER_COLOR: Record<number, string> = {
  1: "var(--green)",
  2: "var(--amber)",
  3: "var(--ink-2)",
  4: "var(--red)",
};

function relTime(iso: string | null): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}

export function SourcesScreen() {
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const sources = useQuery<Source[]>({
    queryKey: ["sources", { page }],
    queryFn: () => api.sources({ limit: PAGE_SIZE, offset: page * PAGE_SIZE, include_text: false }),
    retry: 0,
  });

  const detail = useQuery<Source>({
    queryKey: ["source", selectedId],
    queryFn: () => api.source(selectedId!, { include_text: true }),
    enabled: !!selectedId,
    retry: 0,
  });

  const list = sources.data ?? [];

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="11·SOURCES"
        title="Source Monitor"
        breadcrumb={
          sources.isError
            ? `// api offline`
            : `// page ${page + 1} · ${list.length} sources`
        }
        right={
          <div className="row gap-2">
            <Btn ghost onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
              ◀ PREV
            </Btn>
            <Btn ghost onClick={() => setPage((p) => p + 1)} disabled={list.length < PAGE_SIZE}>
              NEXT ▶
            </Btn>
            <Btn ghost>+ ADD RSS</Btn>
            <Btn primary>RETRY ALL</Btn>
          </div>
        }
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div className="grow" style={{ overflowY: "auto" }}>
            {sources.isLoading && (
              <div style={{ padding: 24, fontSize: 11, color: "var(--ink-3)" }}>
                loading sources...
              </div>
            )}
            {sources.isError && (
              <div style={{ padding: 24, fontSize: 11, color: "var(--red)" }}>
                ⚠ failed to fetch sources: {String(sources.error)}
              </div>
            )}
            {!sources.isLoading && !sources.isError && (
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 90 }}>ID</th>
                    <th>Title</th>
                    <th style={{ width: 130 }}>Publisher</th>
                    <th style={{ width: 70 }}>Trust</th>
                    <th style={{ width: 100 }}>Fetched</th>
                    <th style={{ width: 50 }}>Lang</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((s) => {
                    const tier = s.trust_tier ?? 4;
                    const isSel = s.id === selectedId;
                    return (
                      <tr
                        key={s.id}
                        onClick={() => setSelectedId(s.id)}
                        style={{
                          cursor: "pointer",
                          background: isSel ? "var(--bg-3)" : undefined,
                        }}
                      >
                        <td className="tab muted">{s.id.slice(0, 8)}</td>
                        <td style={{ color: "var(--ink-0)" }}>{truncate(s.title, 80)}</td>
                        <td style={{ color: "var(--ink-1)" }}>{s.publisher ?? "—"}</td>
                        <td>
                          <span
                            className="tt-up"
                            style={{ fontSize: 9, color: TIER_COLOR[tier] }}
                          >
                            T{tier}
                          </span>
                        </td>
                        <td className="tab muted">{relTime(s.fetched_at)}</td>
                        <td className="tab muted">{s.language ?? "—"}</td>
                      </tr>
                    );
                  })}
                  {list.length === 0 && (
                    <tr>
                      <td colSpan={6}>
                        <div
                          style={{
                            padding: 24,
                            textAlign: "center",
                            color: "var(--ink-3)",
                            fontSize: 11,
                          }}
                        >
                          ── no sources on this page ──
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
        <div
          style={{
            width: 360,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          {!selectedId && (
            <div style={{ padding: 14, fontSize: 11, color: "var(--ink-3)" }}>
              ── select a source to inspect raw text ──
            </div>
          )}
          {selectedId && detail.isLoading && (
            <div style={{ padding: 14, fontSize: 11, color: "var(--ink-3)" }}>
              loading...
            </div>
          )}
          {selectedId && detail.data && (
            <div className="col">
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                  SOURCE
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: "var(--ink-0)",
                    marginTop: 4,
                    fontWeight: 600,
                    lineHeight: 1.4,
                  }}
                >
                  {detail.data.title}
                </div>
                <div className="row gap-2" style={{ marginTop: 8, flexWrap: "wrap" }}>
                  <Chip tone="amber">T{detail.data.trust_tier}</Chip>
                  {detail.data.language && <Chip>{detail.data.language}</Chip>}
                  {detail.data.publisher && <Chip>{detail.data.publisher}</Chip>}
                </div>
              </div>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <KV k="ID" v={<span className="tab">{detail.data.id.slice(0, 12)}…</span>} />
                <KV k="Hash" v={<span className="tab">{detail.data.content_hash.slice(0, 10)}…</span>} />
                <KV k="Fetched" v={relTime(detail.data.fetched_at)} />
                <KV k="Published" v={relTime(detail.data.published_at)} />
                <KV k="License" v={detail.data.license ?? "—"} />
                {detail.data.url && (
                  <KV
                    k="URL"
                    v={
                      <a
                        href={detail.data.url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "var(--amber)" }}
                      >
                        open ↗
                      </a>
                    }
                  />
                )}
              </div>
              <div style={{ padding: 14 }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                >
                  RAW TEXT (fragment)
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--ink-1)",
                    background: "var(--bg-2)",
                    border: "1px solid var(--line-1)",
                    padding: 10,
                    lineHeight: 1.55,
                    maxHeight: 320,
                    overflowY: "auto",
                    whiteSpace: "pre-wrap",
                    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  }}
                >
                  {detail.data.raw_text
                    ? detail.data.raw_text.slice(0, 2000) +
                      (detail.data.raw_text.length > 2000 ? "…" : "")
                    : "(no raw text available)"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
