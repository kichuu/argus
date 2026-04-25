"use client";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Bar } from "@/components/ui/Bar";
import { Chip } from "@/components/ui/Chip";
import { MockBadge } from "@/components/ui/MockBadge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type ClaimSummary, type DiscussionSummary } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";

const MOCK_DEBATES = [
  { title: "Apr 25, 2026", quar: 0.42, blo: 0.18, kin: 0.07, status: "current", color: "var(--amber)" },
  { title: "Mar 22, 2026", quar: 0.31, blo: 0.14, kin: 0.05, status: "month ago", color: "var(--p-2)" },
];

type LooseDiscussion = DiscussionSummary & {
  affected_entities?: string[];
  entities?: string[];
};

type LooseClaim = ClaimSummary & {
  status?: string;
};

type LiveDebate = {
  key: string;
  title: string;
  status: string;
  color: string;
  topic: string;
  quar: number;
  blo: number;
  kin: number;
  claimsCount: number;
  affectedEntities: string[];
  newEntities: string[];
};

function formatDebateTitle(d: LooseDiscussion): string {
  const ts = d.completed_at ?? d.started_at ?? d.created_at;
  if (!ts) return d.id.slice(0, 12);
  const dt = new Date(ts);
  if (Number.isNaN(dt.getTime())) return d.id.slice(0, 12);
  const m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${m[dt.getUTCMonth()]} ${dt.getUTCDate()}, ${dt.getUTCFullYear()}`;
}

function meanConfidence(claims: LooseClaim[], onlyLikelyTrue: boolean): number {
  const filtered = onlyLikelyTrue
    ? claims.filter((c) => c.status === "likely_true" && typeof c.confidence === "number")
    : claims.filter((c) => typeof c.confidence === "number");
  if (filtered.length === 0) return 0;
  const sum = filtered.reduce((acc, c) => acc + (c.confidence ?? 0), 0);
  return sum / filtered.length;
}

function deriveProbability(claims: LooseClaim[]): number {
  const lt = meanConfidence(claims, true);
  if (lt > 0) return lt;
  return meanConfidence(claims, false);
}

export function CompareScreen() {
  const discussionsQuery = useQuery({
    queryKey: ["recent-completed"],
    queryFn: api.discussions,
    staleTime: 60_000,
    retry: 0,
  });

  const completed = useMemo<LooseDiscussion[]>(() => {
    const all = (discussionsQuery.data ?? []) as LooseDiscussion[];
    return all
      .filter((d) => d.status === "completed")
      .sort((a, b) => {
        const at = new Date(a.completed_at ?? a.started_at ?? a.created_at ?? 0).getTime();
        const bt = new Date(b.completed_at ?? b.started_at ?? b.created_at ?? 0).getTime();
        return bt - at;
      })
      .slice(0, 2);
  }, [discussionsQuery.data]);

  const claimsQueries = useQueries({
    queries: completed.map((d) => ({
      queryKey: ["discussion-claims", d.id],
      queryFn: () => api.discussionClaims(d.id),
      staleTime: 60_000,
      retry: 0,
    })),
  });

  const status = apiStatus(discussionsQuery);
  const haveLive = completed.length >= 2;

  // Build live debates with derived metrics.
  const liveDebates = useMemo<LiveDebate[]>(() => {
    if (!haveLive) return [];
    const colors = ["var(--amber)", "var(--p-2)"];
    const statuses = ["current", "prior"];
    const claimsByIdx = claimsQueries.map((q) => (q.data ?? []) as LooseClaim[]);
    const entitiesByIdx = completed.map((d) => d.affected_entities ?? d.entities ?? []);

    return completed.map((d, i) => {
      const claims = claimsByIdx[i];
      const probability = deriveProbability(claims);
      // Distribute remaining mass roughly across blo/kin like the mock visual.
      const blo = Math.max(0, Math.min(1, probability * 0.42));
      const kin = Math.max(0, Math.min(1, probability * 0.16));
      const sharedTopic =
        completed.length === 2 && completed[0].topic && completed[0].topic === completed[1].topic;
      const otherIdx = i === 0 ? 1 : 0;
      const otherEntities = new Set(entitiesByIdx[otherIdx] ?? []);
      const newEntities = sharedTopic
        ? (entitiesByIdx[i] ?? []).filter((e) => !otherEntities.has(e))
        : i === 0
          ? entitiesByIdx[i] ?? []
          : [];

      return {
        key: d.id,
        title: formatDebateTitle(d),
        status: statuses[i] ?? "—",
        color: colors[i] ?? "var(--p-3)",
        topic: d.topic ?? "—",
        quar: probability,
        blo,
        kin,
        claimsCount: claims.length,
        affectedEntities: entitiesByIdx[i] ?? [],
        newEntities,
      };
    });
  }, [haveLive, completed, claimsQueries]);

  const claimsLoading = claimsQueries.some((q) => q.isLoading);

  if (discussionsQuery.isLoading) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader code="10·COMPARE" title="Compare Mode" breadcrumb="// loading recent debates" />
        <Skeleton rows={8} rowHeight={20} style={{ padding: 24 }} />
      </div>
    );
  }

  // Fall back to the static mock when fewer than two completed discussions exist.
  if (!haveLive) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader
          code="10·COMPARE"
          title="Compare Mode"
          breadcrumb="// 2 debates · TW Strait Apr-25 vs TW Strait Mar-22"
          right={<MockBadge online={false} loading={status.loading} />}
        />
        <div className="grow row" style={{ overflow: "hidden" }}>
          {MOCK_DEBATES.map((d, i) => {
            const dist: [string, number][] = [
              ["Quarantine", d.quar],
              ["Blockade", d.blo],
              ["Kinetic", d.kin],
              ["Status quo", 1 - d.quar - d.blo - d.kin],
            ];
            return (
              <div
                key={d.title}
                className="grow col"
                style={{
                  borderRight: i === 0 ? "1px solid var(--line-2)" : "none",
                  padding: 24,
                  overflowY: "auto",
                }}
              >
                <div className="row gap-3" style={{ alignItems: "baseline" }}>
                  <div style={{ fontSize: 22, fontWeight: 600, color: d.color }}>{d.title}</div>
                  <Chip tone="amber">{d.status}</Chip>
                </div>
                <div style={{ fontSize: 13, color: "var(--ink-1)", marginTop: 4, lineHeight: 1.5 }}>
                  Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?
                </div>

                <div style={{ marginTop: 24, padding: 18, border: "1px solid var(--line-2)" }}>
                  <div className="tt-up muted" style={{ fontSize: 9 }}>
                    QUARANTINE PROBABILITY
                  </div>
                  <div className="tab" style={{ fontSize: 48, color: d.color, fontWeight: 600 }}>
                    {d.quar.toFixed(2)}
                  </div>
                  {i === 0 && (
                    <div style={{ fontSize: 11, color: "var(--green)" }}>
                      +0.11 vs prior · 35% relative ↑
                    </div>
                  )}
                </div>

                <div style={{ marginTop: 16 }}>
                  <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                    SCENARIO DISTRIBUTION
                  </div>
                  {dist.map(([l, p]) => (
                    <div
                      key={l}
                      className="row gap-2"
                      style={{ alignItems: "center", padding: "4px 0" }}
                    >
                      <span
                        className="tt-up"
                        style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 90 }}
                      >
                        {l}
                      </span>
                      <Bar value={p} max={1} width={200} color={d.color} />
                      <span className="tab" style={{ fontSize: 11, color: "var(--ink-1)" }}>
                        {p.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 24 }}>
                  <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                    NEW ENTITIES SINCE{i === 0 && " MAR-22"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--ink-1)", lineHeight: 1.7 }}>
                    {i === 0 ? (
                      <>
                        · Joint Sword 2026-A
                        <br />· ROCS Hai Kun
                        <br />· INDOPACOM Status FOXTROT
                      </>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </div>
                </div>

                <div style={{ marginTop: 24 }}>
                  <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                    CAST DELTA
                  </div>
                  <div style={{ fontSize: 11, color: "var(--ink-1)" }}>
                    {i === 0 ? (
                      <>
                        <span className="green">+ Ishiba (JP)</span> ·{" "}
                        <span className="green">+ Adm. Paparo</span>
                      </>
                    ) : (
                      "5 personas"
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Live: render two most-recent completed discussions side-by-side.
  const probDelta = liveDebates[0].quar - liveDebates[1].quar;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="10·COMPARE"
        title="Compare Mode"
        breadcrumb={`// 2 debates · ${liveDebates[0].title} vs ${liveDebates[1].title}`}
        right={<MockBadge online={true} loading={false} />}
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        {liveDebates.map((d, i) => {
          const statusQuo = Math.max(0, 1 - d.quar - d.blo - d.kin);
          const dist: [string, number][] = [
            ["Quarantine", d.quar],
            ["Blockade", d.blo],
            ["Kinetic", d.kin],
            ["Status quo", statusQuo],
          ];
          const deltaPct =
            i === 0 && liveDebates[1].quar > 0
              ? Math.round((probDelta / liveDebates[1].quar) * 100)
              : null;
          return (
            <div
              key={d.key}
              className="grow col"
              style={{
                borderRight: i === 0 ? "1px solid var(--line-2)" : "none",
                padding: 24,
                overflowY: "auto",
              }}
            >
              <div className="row gap-3" style={{ alignItems: "baseline" }}>
                <div style={{ fontSize: 22, fontWeight: 600, color: d.color }}>{d.title}</div>
                <Chip tone="amber">{d.status}</Chip>
              </div>
              <div
                style={{
                  fontSize: 13,
                  color: "var(--ink-1)",
                  marginTop: 4,
                  lineHeight: 1.5,
                }}
              >
                {d.topic}
              </div>

              <div style={{ marginTop: 24, padding: 18, border: "1px solid var(--line-2)" }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  MAIN PROBABILITY
                </div>
                <div className="tab" style={{ fontSize: 48, color: d.color, fontWeight: 600 }}>
                  {claimsLoading ? "—" : d.quar.toFixed(2)}
                </div>
                {i === 0 && deltaPct !== null && (
                  <div
                    style={{
                      fontSize: 11,
                      color: probDelta >= 0 ? "var(--green)" : "var(--red)",
                    }}
                  >
                    {probDelta >= 0 ? "+" : ""}
                    {probDelta.toFixed(2)} vs prior · {deltaPct}% relative{" "}
                    {probDelta >= 0 ? "↑" : "↓"}
                  </div>
                )}
              </div>

              <div style={{ marginTop: 16 }}>
                <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                  SCENARIO DISTRIBUTION
                </div>
                {dist.map(([l, p]) => (
                  <div
                    key={l}
                    className="row gap-2"
                    style={{ alignItems: "center", padding: "4px 0" }}
                  >
                    <span
                      className="tt-up"
                      style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 90 }}
                    >
                      {l}
                    </span>
                    <Bar value={p} max={1} width={200} color={d.color} />
                    <span className="tab" style={{ fontSize: 11, color: "var(--ink-1)" }}>
                      {p.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 24 }}>
                <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                  NEW ENTITIES{i === 0 ? " SINCE PRIOR" : ""}
                </div>
                <div style={{ fontSize: 11, color: "var(--ink-1)", lineHeight: 1.7 }}>
                  {d.newEntities.length > 0 ? (
                    d.newEntities.slice(0, 8).map((e, j) => (
                      <span key={`${e}-${j}`}>
                        · {e}
                        <br />
                      </span>
                    ))
                  ) : (
                    <span className="muted">—</span>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 24 }}>
                <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                  CAST DELTA
                </div>
                <div style={{ fontSize: 11, color: "var(--ink-1)" }}>
                  {claimsLoading ? "…" : `${d.claimsCount} claims`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
