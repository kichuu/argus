"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type Claim, type ClaimStatus } from "@/lib/api";
import { ARGUS_DATA, type RecentDebate } from "@/mock/data";

const FALLBACK_EXTRA: RecentDebate[] = [
  { id: "d-2026-04-19-04", title: "Meta-EU AI Act: §50 enforcement first-mover", time: "6d", personas: 5, status: "done" },
  { id: "d-2026-04-18-01", title: "Brazil rate cut: BCB orthodoxy under fiscal stress", time: "7d", personas: 4, status: "done" },
];

const STATUS_OPTIONS: { value: ClaimStatus | "all"; label: string }[] = [
  { value: "all", label: "ALL" },
  { value: "likely_true", label: "LIKELY TRUE" },
  { value: "contested", label: "CONTESTED" },
  { value: "unverified", label: "UNVERIFIED" },
  { value: "likely_false", label: "LIKELY FALSE" },
];

const STATUS_COLOR: Record<ClaimStatus, string> = {
  likely_true: "var(--green)",
  contested: "var(--amber)",
  unverified: "var(--ink-2)",
  likely_false: "var(--red)",
};

const PAGE_SIZE = 50;

function relTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export function LibraryScreen() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | "all">("all");
  const [page, setPage] = useState(0);

  const claims = useQuery<Claim[]>({
    queryKey: ["claims", { status: statusFilter, page }],
    queryFn: () =>
      api.claims({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        ...(statusFilter !== "all" ? { status: statusFilter } : {}),
      }),
    retry: 0,
  });

  const usingFallback = claims.isError;
  const live = claims.data ?? [];
  const filtered = useMemo(
    () => (q ? live.filter((c) => c.statement.toLowerCase().includes(q.toLowerCase())) : live),
    [q, live],
  );

  // Mock fallback when API unreachable.
  const mockItems = useMemo(() => [...ARGUS_DATA.RECENT, ...FALLBACK_EXTRA], []);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="08·LIBRARY"
        title="Claim Library"
        breadcrumb={
          usingFallback
            ? `// api offline · ${mockItems.length} mock entries`
            : `// ${live.length} on this page · status=${statusFilter}`
        }
        right={
          <div className="row gap-2">
            <Btn ghost>+ COLLECTION</Btn>
            <Btn ghost>↗ BULK EXPORT</Btn>
            <Btn ghost>◫ DIFF TWO</Btn>
          </div>
        }
      />
      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          style={{
            width: 220,
            borderRight: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            padding: 14,
            overflowY: "auto",
          }}
        >
          <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 6 }}>
            STATUS
          </div>
          <div className="col gap-1">
            {STATUS_OPTIONS.map((opt) => {
              const active = statusFilter === opt.value;
              return (
                <span
                  key={opt.value}
                  onClick={() => {
                    setStatusFilter(opt.value);
                    setPage(0);
                  }}
                  className={active ? "chip chip-amber" : "chip"}
                  style={{ cursor: "pointer", justifyContent: "flex-start" }}
                >
                  {active ? "■" : "□"} {opt.label}
                </span>
              );
            })}
          </div>
          <div
            className="tt-up"
            style={{ fontSize: 9, color: "var(--ink-3)", margin: "16px 0 6px" }}
          >
            FILTERS
          </div>
          <div className="col gap-1" style={{ fontSize: 10 }}>
            <div>· By topic</div>
            <div>· By persona</div>
            <div>· By date range</div>
            <div>· By region</div>
            <div>· By confidence</div>
          </div>
        </div>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div
            style={{
              padding: 12,
              borderBottom: "1px solid var(--line-2)",
              background: "var(--bg-1)",
              display: "flex",
              gap: 10,
              alignItems: "center",
            }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="input"
              placeholder="search claim statements..."
              style={{ flex: 1 }}
            />
            <Btn ghost onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
              ◀ PREV
            </Btn>
            <span className="tab muted" style={{ fontSize: 10 }}>
              page {page + 1}
            </span>
            <Btn
              ghost
              onClick={() => setPage((p) => p + 1)}
              disabled={live.length < PAGE_SIZE}
            >
              NEXT ▶
            </Btn>
          </div>
          <div className="grow" style={{ overflowY: "auto" }}>
            {claims.isLoading && (
              <div style={{ padding: 24, fontSize: 11, color: "var(--ink-3)" }}>
                loading claims...
              </div>
            )}
            {usingFallback ? (
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Title (mock)</th>
                    <th style={{ width: 110 }}>ID</th>
                    <th style={{ width: 90 }}>Status</th>
                    <th style={{ width: 70 }}>Age</th>
                  </tr>
                </thead>
                <tbody>
                  {mockItems.map((d) => (
                    <tr
                      key={d.id}
                      style={{ cursor: "default" }}
                    >
                      <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                      <td className="tab muted">{d.id}</td>
                      <td>
                        <span
                          className="tt-up"
                          style={{ fontSize: 9, color: "var(--ink-2)" }}
                        >
                          {d.status}
                        </span>
                      </td>
                      <td className="tab muted">{d.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Statement</th>
                    <th style={{ width: 110 }}>ID</th>
                    <th style={{ width: 110 }}>Status</th>
                    <th style={{ width: 110 }}>Confidence</th>
                    <th style={{ width: 60 }}>Sources</th>
                    <th style={{ width: 60 }}>Age</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => {
                    const color = STATUS_COLOR[c.status];
                    return (
                      <tr
                        key={c.id}
                        style={{ cursor: "default" }}
                      >
                        <td style={{ color: "var(--ink-0)", lineHeight: 1.45 }}>
                          {c.statement}
                        </td>
                        <td className="tab muted">{c.id.slice(0, 8)}</td>
                        <td>
                          <span className="tt-up" style={{ fontSize: 9, color }}>
                            {c.status.replace("_", " ")}
                          </span>
                        </td>
                        <td>
                          <Bar value={c.confidence} width={70} color={color} showVal />
                        </td>
                        <td className="tab">
                          {c.supporting_evidence.length}
                          {c.contradicting_evidence.length > 0 && (
                            <span style={{ color: "var(--red)" }}>
                              {" "}
                              −{c.contradicting_evidence.length}
                            </span>
                          )}
                        </td>
                        <td className="tab muted">{relTime(c.created_at)}</td>
                      </tr>
                    );
                  })}
                  {!claims.isLoading && filtered.length === 0 && (
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
                          ── no claims match these filters ──
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
          {usingFallback && (
            <div
              style={{
                padding: 8,
                borderTop: "1px solid var(--line-2)",
                background: "var(--bg-1)",
                fontSize: 10,
              }}
            >
              <Chip tone="amber">FALLBACK MOCK</Chip>{" "}
              <span className="muted">api unreachable — showing archived debates</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
