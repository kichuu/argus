"use client";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Bar } from "@/components/ui/Bar";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { MockBadge } from "@/components/ui/MockBadge";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";

type LooseSource = {
  id: string;
  name?: string;
  type?: string;
  status?: string;
  title?: string;
  publisher?: string;
  trust_tier?: number | null;
  created_at?: string;
  ingested_at?: string;
};

type TickerEntry = { t: string; src: string; line: string };

const TIER_COLOR: Record<string, string> = {
  "1": "var(--green)",
  "2": "var(--amber)",
  "3": "var(--p-3)",
  "4": "var(--red)",
};

const TIER_LABEL: Record<string, string> = {
  "1": "Tier 1 · primary",
  "2": "Tier 2 · reputable",
  "3": "Tier 3 · regional / opinion",
  "4": "Tier 4 · low-trust",
};

function formatTimeAgo(value?: string): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const diff = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

export function WorldView() {
  const sourcesQuery = useQuery({
    queryKey: ["sources-worldview"],
    queryFn: api.sources,
    refetchInterval: 30_000,
    retry: 0,
    staleTime: 30_000,
  });

  const status = apiStatus(sourcesQuery);
  const data = (sourcesQuery.data as LooseSource[] | undefined) ?? [];
  const apiOnline = status.online && data.length > 0;

  // Group by trust_tier (1/2/3/4); rows where trust_tier is missing are
  // bucketed under "—" so they're visible rather than silently dropped.
  const tierBreakdown = useMemo(() => {
    const map = new Map<string, number>();
    for (const s of data) {
      const k = s.trust_tier == null ? "—" : String(s.trust_tier);
      map.set(k, (map.get(k) ?? 0) + 1);
    }
    const order = ["1", "2", "3", "4", "—"];
    return order
      .filter((k) => map.has(k))
      .map((k) => ({ tier: k, count: map.get(k) ?? 0 }));
  }, [data]);

  const totalTiered = tierBreakdown.reduce((a, b) => a + b.count, 0);

  // Top 10 publishers by ingest count.
  const topPublishers = useMemo(() => {
    const m = new Map<string, number>();
    for (const s of data) {
      const name = s.publisher ?? "—";
      m.set(name, (m.get(name) ?? 0) + 1);
    }
    return Array.from(m.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [data]);

  const ticker = useMemo<TickerEntry[]>(() => {
    if (!apiOnline) return [];
    const rows = data.slice();
    rows.sort((a, b) => {
      const at = new Date(a.created_at ?? a.ingested_at ?? 0).getTime();
      const bt = new Date(b.created_at ?? b.ingested_at ?? 0).getTime();
      return bt - at;
    });
    return rows.slice(0, 20).map((s) => {
      const fullTitle = s.title ?? s.name ?? s.id;
      const shortTitle = fullTitle.length > 80 ? `${fullTitle.slice(0, 77)}…` : fullTitle;
      const publisher = s.publisher ?? s.type ?? "src";
      return {
        t: formatTimeAgo(s.created_at ?? s.ingested_at),
        src: publisher,
        line: shortTitle,
      };
    });
  }, [apiOnline, data]);

  const maxPubCount = topPublishers[0]?.count ?? 1;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="02·WORLD"
        title="Sources monitored"
        breadcrumb={`// ${data.length} sources · ${apiOnline ? "live" : status.loading ? "loading…" : "offline"}`}
        right={<MockBadge online={apiOnline} loading={status.loading} />}
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          className="grow col"
          style={{
            overflow: "auto",
            background: "var(--bg-1)",
            padding: 24,
            gap: 20,
          }}
        >
          {sourcesQuery.isLoading ? (
            <Skeleton rows={6} rowHeight={32} gap={10} />
          ) : sourcesQuery.isError ? (
            <ErrorBox
              message="failed to load sources"
              onRetry={() => sourcesQuery.refetch()}
            />
          ) : data.length === 0 ? (
            <EmptyState
              title="No sources ingested yet"
              hint="Add a source from the Sources screen to populate this view."
            />
          ) : (
            <>
              <Panel
                id="T"
                title="Trust tier breakdown"
                sub={`${data.length} sources total`}
              >
                <div style={{ padding: 16 }}>
                  <div
                    style={{
                      display: "flex",
                      width: "100%",
                      height: 16,
                      border: "1px solid var(--line-2)",
                      marginBottom: 14,
                    }}
                  >
                    {tierBreakdown.map((b) => {
                      const pct = totalTiered === 0 ? 0 : (b.count / totalTiered) * 100;
                      if (pct === 0) return null;
                      return (
                        <div
                          key={b.tier}
                          title={`${TIER_LABEL[b.tier] ?? b.tier}: ${b.count}`}
                          style={{
                            width: `${pct}%`,
                            background: TIER_COLOR[b.tier] ?? "var(--ink-2)",
                          }}
                        />
                      );
                    })}
                  </div>
                  {tierBreakdown.map((b) => {
                    const pct = totalTiered === 0 ? 0 : b.count / totalTiered;
                    return (
                      <div
                        key={b.tier}
                        className="row gap-2"
                        style={{ alignItems: "center", padding: "4px 0" }}
                      >
                        <span
                          className="tt-up"
                          style={{
                            fontSize: 10,
                            minWidth: 200,
                            color: "var(--ink-1)",
                          }}
                        >
                          {TIER_LABEL[b.tier] ?? `Tier ${b.tier}`}
                        </span>
                        <Bar
                          value={pct}
                          max={1}
                          width={220}
                          color={TIER_COLOR[b.tier] ?? "var(--ink-2)"}
                        />
                        <span
                          className="tab"
                          style={{ fontSize: 11, color: "var(--ink-0)", minWidth: 30 }}
                        >
                          {b.count}
                        </span>
                        <span
                          className="muted tab"
                          style={{ fontSize: 9, minWidth: 40 }}
                        >
                          {(pct * 100).toFixed(0)}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </Panel>

              <Panel
                id="P"
                title="Top publishers"
                sub={`top ${topPublishers.length} of ${new Set(data.map((s) => s.publisher ?? "—")).size} publishers`}
              >
                <div style={{ padding: 16 }}>
                  {topPublishers.length === 0 ? (
                    <div className="muted" style={{ fontSize: 11 }}>
                      no publisher data
                    </div>
                  ) : (
                    topPublishers.map((p, i) => (
                      <div
                        key={p.name + i}
                        className="row gap-2"
                        style={{
                          alignItems: "center",
                          padding: "5px 0",
                          borderBottom:
                            i < topPublishers.length - 1
                              ? "1px solid var(--line-1)"
                              : "none",
                        }}
                      >
                        <span
                          className="tab amber"
                          style={{ fontSize: 10, minWidth: 22 }}
                        >
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span
                          style={{
                            flex: 1,
                            fontSize: 11,
                            color: "var(--ink-0)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {p.name}
                        </span>
                        <Bar
                          value={p.count}
                          max={maxPubCount}
                          width={140}
                          color="var(--amber)"
                        />
                        <span
                          className="tab"
                          style={{ fontSize: 11, color: "var(--ink-1)", minWidth: 36, textAlign: "right" }}
                        >
                          {p.count}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </Panel>
            </>
          )}
        </div>

        <div
          className="col"
          style={{
            width: 360,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          <Panel
            id="T"
            title="Live ticker"
            sub={apiOnline ? `${ticker.length} · sources` : "—"}
            style={{ flex: 1, border: "none" }}
            right={<MockBadge online={apiOnline} loading={status.loading} />}
          >
            <div className="col" style={{ overflowY: "auto" }}>
              {ticker.length === 0 ? (
                <div style={{ padding: 14 }}>
                  <EmptyState
                    title="No recent ingest"
                    hint="Ingested sources will appear here as they arrive."
                  />
                </div>
              ) : (
                ticker.map((t, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "6px 10px",
                      borderBottom: "1px solid var(--line-1)",
                      fontSize: 10,
                      lineHeight: 1.4,
                    }}
                  >
                    <div className="row gap-2" style={{ alignItems: "baseline" }}>
                      <span className="tab muted">{t.t}</span>
                      <span className="amber tt-up" style={{ fontSize: 9 }}>
                        {t.src}
                      </span>
                    </div>
                    <div style={{ color: "var(--ink-1)", marginTop: 2 }}>{t.line}</div>
                  </div>
                ))
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
