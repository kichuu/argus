"use client";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { useDebateStore } from "@/store/debate";

type LibItem = {
  id: string;
  title: string;
  time: string;
  status: string;
};

// Status filters cover the full discussion lifecycle plus claim-derived
// rollups. Each filter narrows the table and shows its real count.
const STATUS_FILTERS = [
  "all",
  "likely_true",
  "contested",
  "unverified",
  "running",
  "failed",
] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

// Cap on how many discussion-claims fetches we'll fire. Matches the visible
// page on a typical screen and avoids fanning out a request per row when the
// archive grows.
const CLAIMS_FETCH_CAP = 30;

function relTime(iso?: string): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const dMs = Date.now() - t;
  const m = Math.max(0, Math.floor(dMs / 60000));
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

export function LibraryScreen() {
  const router = useRouter();
  const setDiscussionId = useDebateStore((s) => s.setDiscussionId);
  const setTopic = useDebateStore((s) => s.setTopic);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<StatusFilter>("all");

  const remote = useQuery({
    queryKey: ["discussions"],
    queryFn: api.discussions,
    retry: 0,
    staleTime: 30_000,
  });

  const items: LibItem[] =
    remote.data?.map((d) => ({
      id: d.id,
      title: d.topic ?? d.id,
      time: relTime(d.started_at ?? d.created_at ?? d.completed_at),
      status: d.status ?? "unknown",
    })) ?? [];

  // Per-discussion claim fetches — used both for the confidence bar and to
  // bucket each row into a derived claim-status label.
  const liveIds = items.slice(0, CLAIMS_FETCH_CAP).map((i) => i.id);
  const claimsQueries = useQueries({
    queries: liveIds.map((id) => ({
      queryKey: ["discussion-claims", id],
      queryFn: () => api.discussionClaims(id),
      enabled: items.length > 0,
      retry: 0,
      staleTime: 60_000,
    })),
  });

  // id -> { confidence, claimStatus } where claimStatus is the dominant claim
  // status across that discussion (likely_true / contested / unverified).
  type RowMeta = { confidence: number | null; claimStatus: StatusFilter | null };
  const metaById = useMemo(() => {
    const map = new Map<string, RowMeta>();
    liveIds.forEach((id, idx) => {
      const data = (claimsQueries[idx]?.data ?? []) as Array<{
        confidence?: number;
        status?: string;
      }>;
      const vals = data
        .map((c) => c.confidence)
        .filter((v): v is number => typeof v === "number" && !Number.isNaN(v));
      const confidence =
        vals.length === 0 ? null : Math.max(0, Math.min(1, vals.reduce((a, b) => a + b, 0) / vals.length));

      const buckets: Record<string, number> = {};
      for (const c of data) {
        const s = c.status;
        if (s === "likely_true" || s === "contested" || s === "unverified") {
          buckets[s] = (buckets[s] ?? 0) + 1;
        }
      }
      let claimStatus: StatusFilter | null = null;
      let max = 0;
      for (const k of ["likely_true", "contested", "unverified"] as const) {
        if ((buckets[k] ?? 0) > max) {
          max = buckets[k];
          claimStatus = k;
        }
      }
      map.set(id, { confidence, claimStatus });
    });
    return map;
  }, [liveIds, claimsQueries]);

  // Derived counts per filter, computed off the same data.
  const counts = useMemo(() => {
    const c: Record<StatusFilter, number> = {
      all: items.length,
      likely_true: 0,
      contested: 0,
      unverified: 0,
      running: 0,
      failed: 0,
    };
    for (const it of items) {
      if (it.status === "running") c.running += 1;
      if (it.status === "failed") c.failed += 1;
      const meta = metaById.get(it.id);
      if (meta?.claimStatus) c[meta.claimStatus] += 1;
    }
    return c;
  }, [items, metaById]);

  const filtered = useMemo(() => {
    let rows = items;
    if (filter !== "all") {
      if (filter === "running" || filter === "failed") {
        rows = rows.filter((r) => r.status === filter);
      } else {
        rows = rows.filter((r) => metaById.get(r.id)?.claimStatus === filter);
      }
    }
    if (q) {
      rows = rows.filter((i) => i.title.toLowerCase().includes(q.toLowerCase()));
    }
    return rows;
  }, [items, filter, metaById, q]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="08·LIBRARY"
        title="Synthesis Library"
        breadcrumb={`// ${items.length} discussions · ${remote.isSuccess ? "live" : remote.isLoading ? "loading…" : "offline"}`}
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {remote.isSuccess && <Chip tone="green">live · {items.length}</Chip>}
            {remote.isError && <Chip tone="amber">offline</Chip>}
            <Btn ghost>↗ BULK EXPORT</Btn>
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
          {STATUS_FILTERS.map((f) => {
            const sel = f === filter;
            const label = f === "all" ? "All" : f.replace(/_/g, " ");
            return (
              <div
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding: "5px 8px",
                  display: "flex",
                  fontSize: 11,
                  color: sel ? "var(--amber)" : "var(--ink-1)",
                  background: sel ? "var(--bg-3)" : "transparent",
                  cursor: "pointer",
                  borderLeft: sel ? "2px solid var(--amber)" : "2px solid transparent",
                  textTransform: "capitalize",
                }}
              >
                <span style={{ flex: 1 }}>{label}</span>
                <span className="tab muted">{counts[f]}</span>
              </div>
            );
          })}
        </div>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div
            style={{ padding: 12, borderBottom: "1px solid var(--line-2)", background: "var(--bg-1)" }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="input"
              placeholder="search debates"
            />
          </div>
          <div className="grow" style={{ overflowY: "auto" }}>
            {remote.isLoading ? (
              <Skeleton rows={5} rowHeight={20} style={{ padding: 16 }} />
            ) : remote.isError ? (
              <ErrorBox
                message="failed to load discussions"
                onRetry={() => remote.refetch()}
                style={{ margin: 16 }}
              />
            ) : items.length === 0 ? (
              <EmptyState
                title="No saved debates yet"
                hint="Launch one from Home"
                cta={{ label: "GO HOME", onClick: () => router.push("/") }}
                style={{ margin: 16 }}
              />
            ) : filtered.length === 0 ? (
              <EmptyState
                title="No debates match this filter"
                hint={`Try a different status or clear the search.`}
                style={{ margin: 16 }}
              />
            ) : (
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th style={{ width: 120 }}>ID</th>
                    <th style={{ width: 110 }}>Confidence</th>
                    <th style={{ width: 110 }}>Status</th>
                    <th style={{ width: 60 }}>Age</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((d) => {
                    const meta = metaById.get(d.id);
                    const conf = meta?.confidence ?? null;
                    const claimStatus = meta?.claimStatus;
                    return (
                      <tr
                        key={d.id}
                        onClick={() => {
                          setDiscussionId(d.id);
                          setTopic(d.title);
                          router.push(d.status === "running" ? "/ops" : "/synthesis");
                        }}
                        style={{ cursor: "pointer" }}
                      >
                        <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                        <td className="tab muted">{d.id}</td>
                        <td>
                          {conf != null ? (
                            <Bar value={conf} max={1} width={80} color="var(--amber)" />
                          ) : (
                            <span className="muted" style={{ fontSize: 10 }}>—</span>
                          )}
                        </td>
                        <td>
                          <span
                            className="tt-up"
                            style={{
                              fontSize: 9,
                              color:
                                d.status === "running"
                                  ? "var(--amber)"
                                  : d.status === "failed"
                                    ? "var(--red)"
                                    : claimStatus === "likely_true"
                                      ? "var(--green)"
                                      : claimStatus === "contested"
                                        ? "var(--amber)"
                                        : claimStatus === "unverified"
                                          ? "var(--red)"
                                          : "var(--ink-2)",
                            }}
                          >
                            {claimStatus ?? d.status}
                          </span>
                        </td>
                        <td className="tab muted">{d.time}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
