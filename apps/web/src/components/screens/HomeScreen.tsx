"use client";
import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { useDebateStore } from "@/store/debate";

function relTime(iso?: string): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const dMs = Math.max(0, Date.now() - t);
  const m = Math.floor(dMs / 60000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

type ActivityRow = {
  key: string;
  kind: "discussion" | "claim" | "source";
  label: string;
  detail?: string;
  ts: number;
  status?: string;
};

export function HomeScreen() {
  const router = useRouter();
  const setTopic = useDebateStore((s) => s.setTopic);
  const setDiscussionId = useDebateStore((s) => s.setDiscussionId);
  const [prompt, setPrompt] = useState("");
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("standard");
  const [autoPersonas, setAutoPersonas] = useState<boolean>(true);
  const [sources, setSources] = useState({ rss: true, news: true, social: true, kg: true });
  const [launchError, setLaunchError] = useState<string | null>(null);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: 0,
    staleTime: 30_000,
  });

  const suggested = useQuery({
    queryKey: ["suggested-topics"],
    queryFn: () => api.suggestedTopics({ limit: 5 }),
    retry: 0,
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
  const liveTopics = suggested.data?.topics ?? [];

  // Recent activity: parallel-fetch discussions / claims / sources, take most
  // recent of each kind. No /activity endpoint exists; this is the fallback
  // composition documented in the brief.
  const activityQueries = useQueries({
    queries: [
      {
        queryKey: ["activity-discussions"],
        queryFn: api.discussions,
        retry: 0,
        staleTime: 60_000,
      },
      {
        queryKey: ["activity-claims"],
        queryFn: api.claims,
        retry: 0,
        staleTime: 60_000,
      },
      {
        queryKey: ["activity-sources"],
        queryFn: api.sources,
        retry: 0,
        staleTime: 60_000,
      },
    ],
  });

  const [discussionsQ, claimsQ, sourcesQ] = activityQueries;
  const activityLoading = activityQueries.some((q) => q.isLoading);
  const activityError = activityQueries.every((q) => q.isError);

  const recentActivity = useMemo<ActivityRow[]>(() => {
    const rows: ActivityRow[] = [];
    type LooseDisc = {
      id: string;
      topic?: string;
      status?: string;
      created_at?: string;
      started_at?: string;
      completed_at?: string;
    };
    type LooseClaim = {
      id: string;
      text?: string;
      subject?: string;
      predicate?: string;
      object?: string;
      created_at?: string;
      confidence?: number;
    };
    type LooseSource = {
      id: string;
      name?: string;
      title?: string;
      publisher?: string;
      created_at?: string;
      ingested_at?: string;
    };

    const disc = ((discussionsQ.data as LooseDisc[] | undefined) ?? [])
      .slice()
      .sort((a, b) => {
        const at = Date.parse(a.completed_at ?? a.started_at ?? a.created_at ?? "") || 0;
        const bt = Date.parse(b.completed_at ?? b.started_at ?? b.created_at ?? "") || 0;
        return bt - at;
      })
      .slice(0, 3);
    for (const d of disc) {
      const ts =
        Date.parse(d.completed_at ?? d.started_at ?? d.created_at ?? "") || 0;
      rows.push({
        key: `d-${d.id}`,
        kind: "discussion",
        label: d.topic ?? d.id,
        detail: d.status,
        ts,
        status: d.status,
      });
    }

    const claims = ((claimsQ.data as LooseClaim[] | undefined) ?? [])
      .slice()
      .sort((a, b) => {
        const at = Date.parse(a.created_at ?? "") || 0;
        const bt = Date.parse(b.created_at ?? "") || 0;
        return bt - at;
      })
      .slice(0, 3);
    for (const c of claims) {
      const text =
        c.text ?? [c.subject, c.predicate, c.object].filter(Boolean).join(" ") || c.id;
      rows.push({
        key: `c-${c.id}`,
        kind: "claim",
        label: text,
        detail:
          typeof c.confidence === "number" ? `conf ${c.confidence.toFixed(2)}` : undefined,
        ts: Date.parse(c.created_at ?? "") || 0,
      });
    }

    const srcs = ((sourcesQ.data as LooseSource[] | undefined) ?? [])
      .slice()
      .sort((a, b) => {
        const at = Date.parse(a.created_at ?? a.ingested_at ?? "") || 0;
        const bt = Date.parse(b.created_at ?? b.ingested_at ?? "") || 0;
        return bt - at;
      })
      .slice(0, 3);
    for (const s of srcs) {
      rows.push({
        key: `s-${s.id}`,
        kind: "source",
        label: s.title ?? s.name ?? s.id,
        detail: s.publisher,
        ts: Date.parse(s.created_at ?? s.ingested_at ?? "") || 0,
      });
    }

    return rows.sort((a, b) => b.ts - a.ts).slice(0, 5);
  }, [discussionsQ.data, claimsQ.data, sourcesQ.data]);

  const startMutation = useMutation({
    mutationFn: (body: Parameters<typeof api.startDiscussion>[0]) =>
      api.startDiscussion(body),
    retry: 0,
  });

  const launch = (text?: string) => {
    const topic = text || prompt;
    if (!topic) {
      setLaunchError("Enter a topic before launching.");
      return;
    }
    setTopic(topic);
    setLaunchError(null);

    const source_kinds = (
      ["rss", "news", "social", "kg"] as const
    ).filter((k) => sources[k]);

    startMutation.mutate(
      {
        topic,
        vertical: "geopolitics",
        depth,
        source_kinds,
        auto_personas: autoPersonas,
      },
      {
        onSuccess: (res) => {
          setDiscussionId(res.id);
          router.push("/ops");
        },
        onError: (err) => {
          setDiscussionId(null);
          setLaunchError(err instanceof Error ? err.message : "launch failed");
        },
      },
    );
  };

  const apiOnline = health.isSuccess;
  const freshnessLabel = health.isLoading
    ? "checking..."
    : apiOnline
      ? `api online · ${health.data?.status ?? "ok"}${health.data?.version ? ` · v${health.data.version}` : ""}`
      : "api offline";

  return (
    <div className="col grow" style={{ padding: 16, gap: 16, overflowY: "auto" }}>
      <ScreenHeader
        code="01·HOME"
        title="Topic Launcher"
        breadcrumb="// convene a council"
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {health.isLoading ? (
              <Skeleton rows={1} rowHeight={10} style={{ padding: 0, width: 140 }} />
            ) : (
              <>
                <Dot tone={apiOnline ? "green" : "amber"} pulse={!apiOnline} />
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  {freshnessLabel}
                </span>
              </>
            )}
          </div>
        }
      />

      {health.isError && (
        <ErrorBox
          message="api health check failed"
          onRetry={() => health.refetch()}
        />
      )}

      <div className="row gap-4" style={{ flexShrink: 0 }}>
        <Panel
          id="A"
          title="New Deliberation"
          sub="multi-agent · world-state grounded"
          style={{ flex: 2, minHeight: 300 }}
        >
          <div className="col grow" style={{ padding: 20, gap: 14 }}>
            <div className="tt-up" style={{ color: "var(--ink-3)", fontSize: 9 }}>
              Topic / question
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?

Personas, world state, citation strictness will be auto-cast from this prompt."
              style={{
                background: "var(--bg-1)",
                border: "1px solid var(--line-2)",
                color: "var(--ink-0)",
                padding: 14,
                fontFamily: "inherit",
                fontSize: 14,
                lineHeight: 1.5,
                resize: "none",
                outline: "none",
                minHeight: 130,
                width: "100%",
              }}
            />
            <div className="row gap-3" style={{ flexWrap: "wrap", alignItems: "center" }}>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  Depth
                </span>
                <Segmented
                  options={[
                    { value: "quick", label: "Quick · 3p" },
                    { value: "standard", label: "Standard · 5p" },
                    { value: "deep", label: "Deep · 7p" },
                  ]}
                  value={depth}
                  onChange={setDepth}
                />
              </div>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  Persona casting
                </span>
                <Segmented
                  options={[
                    { value: true, label: "Auto" },
                    { value: false, label: "Manual" },
                  ]}
                  value={autoPersonas}
                  onChange={setAutoPersonas}
                />
              </div>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  Sources
                </span>
                <div className="row gap-1">
                  {(
                    [
                      ["rss", "RSS"],
                      ["news", "News"],
                      ["social", "Social"],
                      ["kg", "KG only"],
                    ] as const
                  ).map(([k, lbl]) => (
                    <span
                      key={k}
                      onClick={() => setSources((s) => ({ ...s, [k]: !s[k] }))}
                      className={sources[k] ? "chip chip-amber" : "chip"}
                      style={{ cursor: "pointer" }}
                    >
                      {sources[k] ? "■" : "□"} {lbl}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ flex: 1 }} />
            <div className="row gap-2" style={{ alignItems: "center" }}>
              <Btn primary onClick={() => launch()}>
                {startMutation.isPending ? "▸ LAUNCHING..." : "▸ CONVENE COUNCIL"}
              </Btn>
              {launchError && <Chip tone="amber">{launchError}</Chip>}
            </div>
          </div>
        </Panel>

        <Panel
          id="B"
          title="Suggested Topics"
          sub={
            suggested.isSuccess
              ? `live · ${suggested.data?.claim_basis_count ?? 0} recent claims`
              : suggested.isLoading
                ? "loading…"
                : "—"
          }
          style={{ flex: 1, minHeight: 300 }}
          right={
            suggested.isSuccess && liveTopics.length > 0 ? (
              <Chip tone="green">{liveTopics.length}</Chip>
            ) : null
          }
        >
          <div className="col" style={{ overflowY: "auto" }}>
            {suggested.isLoading ? (
              <Skeleton rows={5} rowHeight={20} style={{ padding: 16 }} />
            ) : suggested.isError ? (
              <ErrorBox
                message="failed to load suggested topics"
                onRetry={() => suggested.refetch()}
                style={{ margin: 16 }}
              />
            ) : liveTopics.length === 0 ? (
              <EmptyState
                title="No suggestions yet — ingest more sources"
                hint="Suggested topics are derived from recent claim activity."
                style={{ margin: 16 }}
              />
            ) : (
              liveTopics.map((topic, i) => (
                <div
                  key={topic.id || i}
                  onClick={() => launch(topic.title)}
                  style={{
                    padding: "10px 12px",
                    borderBottom: "1px solid var(--line-1)",
                    cursor: "pointer",
                    display: "flex",
                    gap: 8,
                    alignItems: "flex-start",
                  }}
                >
                  <span
                    className="tab"
                    style={{ color: "var(--amber)", fontSize: 10, minWidth: 18 }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}
                  >
                    <span style={{ fontSize: 11, color: "var(--ink-0)", lineHeight: 1.4 }}>
                      {topic.title}
                    </span>
                    {topic.rationale && (
                      <span
                        className="muted"
                        style={{ fontSize: 9, color: "var(--ink-2)", lineHeight: 1.4 }}
                      >
                        {topic.rationale}
                      </span>
                    )}
                  </span>
                  <span style={{ color: "var(--green)", fontSize: 10 }}>↗</span>
                </div>
              ))
            )}
          </div>
        </Panel>
      </div>

      <div className="row gap-4" style={{ flexShrink: 0, minHeight: 240 }}>
        <Panel
          id="C"
          title="Recent activity"
          sub={
            activityLoading
              ? "loading…"
              : `${recentActivity.length} · discussions / claims / sources`
          }
          style={{ flex: 1 }}
        >
          <div className="col" style={{ overflowY: "auto" }}>
            {activityLoading ? (
              <Skeleton rows={5} rowHeight={22} style={{ padding: 16 }} />
            ) : activityError ? (
              <ErrorBox
                message="failed to load recent activity"
                onRetry={() => {
                  for (const q of activityQueries) q.refetch();
                }}
                style={{ margin: 16 }}
              />
            ) : recentActivity.length === 0 ? (
              <EmptyState
                title="No activity yet"
                hint="Launch a debate or ingest sources to populate this panel."
                style={{ margin: 16 }}
              />
            ) : (
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 78 }}>Kind</th>
                    <th>Item</th>
                    <th style={{ width: 80 }}>Detail</th>
                    <th style={{ width: 60 }}>Age</th>
                    <th style={{ width: 30 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.map((row) => (
                    <tr
                      key={row.key}
                      onClick={() => {
                        if (row.kind === "discussion") {
                          const id = row.key.slice(2);
                          setDiscussionId(id);
                          setTopic(row.label);
                          router.push(
                            row.status === "running" ? "/ops" : "/synthesis",
                          );
                        } else if (row.kind === "source") {
                          router.push("/sources");
                        } else {
                          router.push("/synthesis");
                        }
                      }}
                      style={{ cursor: "pointer" }}
                    >
                      <td>
                        <span
                          className="tt-up"
                          style={{
                            fontSize: 9,
                            color:
                              row.kind === "discussion"
                                ? "var(--amber)"
                                : row.kind === "claim"
                                  ? "var(--green)"
                                  : "var(--ink-2)",
                          }}
                        >
                          {row.kind}
                        </span>
                      </td>
                      <td
                        style={{
                          color: "var(--ink-0)",
                          maxWidth: 0,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {row.label}
                      </td>
                      <td className="tab muted" style={{ fontSize: 10 }}>
                        {row.detail ?? "—"}
                      </td>
                      <td className="tab muted">
                        {row.ts > 0 ? relTime(new Date(row.ts).toISOString()) : "—"}
                      </td>
                      <td className="muted">→</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
