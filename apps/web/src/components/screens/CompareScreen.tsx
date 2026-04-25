"use client";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Bar } from "@/components/ui/Bar";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockBadge } from "@/components/ui/MockBadge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type ClaimSummary, type DiscussionSummary } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";

type LooseDiscussion = DiscussionSummary & {
  affected_entities?: string[];
  entities?: string[];
};

type LooseClaim = ClaimSummary & {
  status?: string;
};

type ClaimDist = {
  likely_true: number;
  contested: number;
  unverified: number;
};

type LiveDebate = {
  key: string;
  title: string;
  status: string;
  color: string;
  topic: string;
  meanConfidence: number;
  claimsCount: number;
  messagesCount: number;
  dist: ClaimDist;
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

function meanConfidence(claims: LooseClaim[]): number {
  const vals = claims
    .map((c) => c.confidence)
    .filter((v): v is number => typeof v === "number" && !Number.isNaN(v));
  if (vals.length === 0) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function bucketize(claims: LooseClaim[]): ClaimDist {
  const d: ClaimDist = { likely_true: 0, contested: 0, unverified: 0 };
  for (const c of claims) {
    const s = c.status;
    if (s === "likely_true") d.likely_true += 1;
    else if (s === "contested") d.contested += 1;
    else d.unverified += 1;
  }
  return d;
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

  const messagesQueries = useQueries({
    queries: completed.map((d) => ({
      queryKey: ["discussion-messages", d.id],
      queryFn: () => api.discussionMessages(d.id),
      staleTime: 60_000,
      retry: 0,
    })),
  });

  const status = apiStatus(discussionsQuery);
  const haveLive = completed.length >= 2;

  const liveDebates = useMemo<LiveDebate[]>(() => {
    if (!haveLive) return [];
    const colors = ["var(--amber)", "var(--p-2)"];
    const statuses = ["current", "prior"];
    const claimsByIdx = claimsQueries.map((q) => (q.data ?? []) as LooseClaim[]);
    const messagesByIdx = messagesQueries.map((q) => q.data ?? []);
    const entitiesByIdx = completed.map((d) => d.affected_entities ?? d.entities ?? []);

    return completed.map((d, i) => {
      const claims = claimsByIdx[i];
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
        meanConfidence: meanConfidence(claims),
        claimsCount: claims.length,
        messagesCount: messagesByIdx[i].length,
        dist: bucketize(claims),
        affectedEntities: entitiesByIdx[i] ?? [],
        newEntities,
      };
    });
  }, [haveLive, completed, claimsQueries, messagesQueries]);

  const claimsLoading = claimsQueries.some((q) => q.isLoading);
  const messagesLoading = messagesQueries.some((q) => q.isLoading);

  if (discussionsQuery.isLoading) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader code="10·COMPARE" title="Compare Mode" breadcrumb="// loading recent debates" />
        <Skeleton rows={8} rowHeight={20} style={{ padding: 24 }} />
      </div>
    );
  }

  if (!haveLive) {
    return (
      <div className="col grow" style={{ overflow: "hidden" }}>
        <ScreenHeader
          code="10·COMPARE"
          title="Compare Mode"
          breadcrumb={`// ${completed.length} completed · need 2`}
          right={<MockBadge online={status.online} loading={status.loading} />}
        />
        <div className="grow col center" style={{ padding: 24 }}>
          <EmptyState
            title="Need 2 completed debates to compare"
            hint="Run more debates to enable side-by-side analysis."
          />
        </div>
      </div>
    );
  }

  const confDelta = liveDebates[0].meanConfidence - liveDebates[1].meanConfidence;
  const msgDelta = liveDebates[0].messagesCount - liveDebates[1].messagesCount;

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
          const total = d.dist.likely_true + d.dist.contested + d.dist.unverified;
          const pct = (n: number) => (total === 0 ? 0 : n / total);
          const histRows: { lbl: string; n: number; p: number; color: string }[] = [
            { lbl: "Likely true", n: d.dist.likely_true, p: pct(d.dist.likely_true), color: "var(--green)" },
            { lbl: "Contested", n: d.dist.contested, p: pct(d.dist.contested), color: "var(--amber)" },
            { lbl: "Unverified", n: d.dist.unverified, p: pct(d.dist.unverified), color: "var(--red)" },
          ];
          const deltaPct =
            i === 0 && liveDebates[1].meanConfidence > 0
              ? Math.round((confDelta / liveDebates[1].meanConfidence) * 100)
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
                  MEAN CONFIDENCE
                </div>
                <div className="tab" style={{ fontSize: 48, color: d.color, fontWeight: 600 }}>
                  {claimsLoading ? "—" : d.meanConfidence.toFixed(2)}
                </div>
                {i === 0 && deltaPct !== null && (
                  <div
                    style={{
                      fontSize: 11,
                      color: confDelta >= 0 ? "var(--green)" : "var(--red)",
                    }}
                  >
                    {confDelta >= 0 ? "+" : ""}
                    {confDelta.toFixed(2)} vs prior · {deltaPct}% relative{" "}
                    {confDelta >= 0 ? "↑" : "↓"}
                  </div>
                )}
              </div>

              <div style={{ marginTop: 16 }}>
                <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                  CLAIM STATUS · {d.claimsCount} claims
                </div>
                {total === 0 ? (
                  <div className="muted" style={{ fontSize: 10 }}>no claims</div>
                ) : (
                  histRows.map((r) => (
                    <div
                      key={r.lbl}
                      className="row gap-2"
                      style={{ alignItems: "center", padding: "4px 0" }}
                    >
                      <span
                        className="tt-up"
                        style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 90 }}
                      >
                        {r.lbl}
                      </span>
                      <Bar value={r.p} max={1} width={200} color={r.color} />
                      <span className="tab" style={{ fontSize: 11, color: "var(--ink-1)" }}>
                        {r.n}
                      </span>
                    </div>
                  ))
                )}
              </div>

              {d.newEntities.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                    NEW ENTITIES{i === 0 ? " SINCE PRIOR" : ""}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--ink-1)", lineHeight: 1.7 }}>
                    {d.newEntities.slice(0, 8).map((e, j) => (
                      <span key={`${e}-${j}`}>
                        · {e}
                        <br />
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ marginTop: 24 }}>
                <div className="tt-up muted" style={{ fontSize: 9, marginBottom: 8 }}>
                  CAST DELTA
                </div>
                <div style={{ fontSize: 11, color: "var(--ink-1)" }}>
                  {messagesLoading
                    ? "…"
                    : i === 0
                      ? `${d.messagesCount} messages · ${msgDelta >= 0 ? "+" : ""}${msgDelta} vs prior`
                      : `${d.messagesCount} messages`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
