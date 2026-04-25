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
import { ARGUS_DATA } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

const COLLECTIONS = [
  { n: "★ Starred", c: 4 },
  { n: "Indo-Pacific", c: 12 },
  { n: "Macro", c: 8 },
  { n: "AI policy", c: 5 },
  { n: "Climate", c: 3 },
  { n: "Recurring", c: 2 },
];

const EXTRA_ITEMS = [
  { id: "d-2026-04-19-04", title: "Meta-EU AI Act: §50 enforcement first-mover", time: "6d", personas: 5, status: "done" as const },
  { id: "d-2026-04-18-01", title: "Brazil rate cut: BCB orthodoxy under fiscal stress", time: "7d", personas: 4, status: "done" as const },
  { id: "d-2026-04-17-02", title: "Iran-Israel: shadow war calibration", time: "8d", personas: 6, status: "done" as const },
  { id: "d-2026-04-15-03", title: "Taiwan preparedness: civil-defense reforms", time: "10d", personas: 5, status: "done" as const },
  { id: "d-2026-04-12-04", title: "ECB September: cut vs. hold", time: "13d", personas: 4, status: "done" as const },
  { id: "d-2026-04-10-01", title: "Ukraine peace deal: territorial freeze scenarios", time: "15d", personas: 6, status: "done" as const },
];

type LibItem = {
  id: string;
  title: string;
  time: string;
  personas: number;
  status: "running" | "done";
};

// Cap on how many discussion-claims fetches we'll fire. Matches the visible
// page on a typical screen and avoids fanning out a request per row when the
// archive grows.
const CLAIMS_FETCH_CAP = 30;
// Default confidence used when a discussion has zero claims yet.
const FALLBACK_CONFIDENCE = 0.6;

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
  const [selected, setSelected] = useState("All debates");

  const remote = useQuery({
    queryKey: ["discussions"],
    queryFn: api.discussions,
    retry: 0,
    staleTime: 30_000,
  });

  const remoteItems: LibItem[] =
    remote.data?.map((d) => ({
      id: d.id,
      title: d.topic ?? d.id,
      time: relTime(d.started_at ?? d.created_at ?? d.completed_at),
      personas: 0,
      status: (d.status === "running" ? "running" : "done") as "running" | "done",
    })) ?? [];

  const apiOnline = remote.isSuccess && remoteItems.length > 0;
  const items: LibItem[] = apiOnline
    ? remoteItems
    : ([...ARGUS_DATA.RECENT, ...EXTRA_ITEMS] as LibItem[]);

  // Fire a per-discussion claims fetch (up to CLAIMS_FETCH_CAP) so we can
  // derive a real mean-confidence bar. Each id is keyed independently in the
  // TanStack cache, so this is shared with /synthesis etc.
  const liveIds = apiOnline ? remoteItems.slice(0, CLAIMS_FETCH_CAP).map((i) => i.id) : [];
  const claimsQueries = useQueries({
    queries: liveIds.map((id) => ({
      queryKey: ["discussion-claims", id],
      queryFn: () => api.discussionClaims(id),
      enabled: apiOnline,
      retry: 0,
      staleTime: 60_000,
    })),
  });

  // id -> mean confidence across that discussion's claims (or fallback).
  const confidenceById = useMemo(() => {
    const map = new Map<string, number>();
    liveIds.forEach((id, idx) => {
      const data = claimsQueries[idx]?.data ?? [];
      const vals = data
        .map((c) => c.confidence)
        .filter((v): v is number => typeof v === "number" && !Number.isNaN(v));
      if (vals.length === 0) {
        map.set(id, FALLBACK_CONFIDENCE);
        return;
      }
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      map.set(id, Math.max(0, Math.min(1, mean)));
    });
    return map;
  }, [liveIds, claimsQueries]);

  const filtered = q
    ? items.filter((i) => i.title.toLowerCase().includes(q.toLowerCase()))
    : items;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="08·LIBRARY"
        title="Synthesis Library"
        breadcrumb={`// ${items.length} archived · ${COLLECTIONS.length + 1} collections · ${apiOnline ? "api online" : "api offline · using mock"}`}
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {!apiOnline && <Chip tone="amber">offline · mock</Chip>}
            {apiOnline && <Chip tone="green">live · {items.length}</Chip>}
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
            COLLECTIONS
          </div>
          {[{ n: "All debates", c: items.length }, ...COLLECTIONS].map((c) => {
            const sel = c.n === selected;
            return (
              <div
                key={c.n}
                onClick={() => setSelected(c.n)}
                style={{
                  padding: "5px 8px",
                  display: "flex",
                  fontSize: 11,
                  color: sel ? "var(--amber)" : "var(--ink-1)",
                  background: sel ? "var(--bg-3)" : "transparent",
                  cursor: "pointer",
                  borderLeft: sel ? "2px solid var(--amber)" : "2px solid transparent",
                }}
              >
                <span style={{ flex: 1 }}>{c.n}</span>
                <span className="tab muted">{c.c}</span>
              </div>
            );
          })}
          <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", margin: "16px 0 6px" }}>
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
            style={{ padding: 12, borderBottom: "1px solid var(--line-2)", background: "var(--bg-1)" }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="input"
              placeholder="search debates · regex supported"
            />
          </div>
          <div className="grow" style={{ overflowY: "auto" }}>
            {remote.isLoading ? (
              <Skeleton rows={5} rowHeight={20} style={{ padding: 16 }} />
            ) : remote.isError && items.length === 0 ? (
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
            ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 24 }}></th>
                  <th>Title</th>
                  <th style={{ width: 90 }}>ID</th>
                  <th style={{ width: 70 }}>Personas</th>
                  <th style={{ width: 100 }}>Confidence</th>
                  <th style={{ width: 70 }}>Status</th>
                  <th style={{ width: 60 }}>Age</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => {
                  // Live: derive from cached per-discussion claims (mean conf,
                  // fallback to 0.6 if no claims yet). Offline: keep the
                  // original heuristic so the mock view still has visual variety.
                  const conf = apiOnline
                    ? confidenceById.get(d.id) ?? FALLBACK_CONFIDENCE
                    : 0.55 + (i % 7) * 0.04;
                  return (
                  <tr
                    key={d.id}
                    onClick={() => {
                      // only set live id when it came from the backend
                      if (apiOnline) {
                        setDiscussionId(d.id);
                        setTopic(d.title);
                      } else {
                        setDiscussionId(null);
                      }
                      router.push(d.status === "running" ? "/ops" : "/synthesis");
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <td>{i % 5 === 2 ? "★" : ""}</td>
                    <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                    <td className="tab muted">{d.id}</td>
                    <td className="tab">{d.personas}</td>
                    <td>
                      <Bar value={conf} max={1} width={80} color="var(--amber)" />
                    </td>
                    <td>
                      <span
                        className="tt-up"
                        style={{
                          fontSize: 9,
                          color: d.status === "running" ? "var(--amber)" : "var(--green)",
                        }}
                      >
                        {d.status}
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
