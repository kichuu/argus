"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AddSourceModal } from "@/components/ui/AddSourceModal";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { EmptyState } from "@/components/ui/EmptyState";
import { KV } from "@/components/ui/KV";
import { MockBadge } from "@/components/ui/MockBadge";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { Sparkline } from "@/components/ui/Sparkline";
import { api, type SourceIngestResponse } from "@/lib/api";
import { ARGUS_DATA } from "@/mock/data";

export function SourcesScreen() {
  const queryClient = useQueryClient();
  const remote = useQuery({
    queryKey: ["sources"],
    queryFn: api.sources,
    retry: 0,
    staleTime: 30_000,
  });

  const stats = useQuery({
    queryKey: ["source-stats"],
    queryFn: api.sourceStats,
    retry: 0,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [lastIngest, setLastIngest] = useState<SourceIngestResponse | null>(null);

  const sources = remote.data && remote.data.length > 0 ? null : ARGUS_DATA.SOURCES;
  const apiOnline = remote.isSuccess && (remote.data?.length ?? 0) > 0;

  async function handleIngested(result: SourceIngestResponse) {
    setLastIngest(result);
    await queryClient.invalidateQueries({ queryKey: ["sources"] });
  }

  async function handleExtractClaims() {
    if (!lastIngest) return;
    try {
      await api.startDiscussion({
        topic: `Extract and verify claims from: ${lastIngest.title}`,
      });
    } catch {
      // Best-effort — keep the ingest banner visible if discussion start fails.
    } finally {
      setLastIngest(null);
    }
  }

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="11·SOURCES"
        title="Source Monitor"
        breadcrumb={`// ${apiOnline ? remote.data!.length : ARGUS_DATA.SOURCES.length} sources · ${apiOnline ? "live" : "mock"}`}
        right={
          <div className="row gap-2">
            <Btn ghost onClick={() => setModalOpen(true)}>
              + INGEST URL
            </Btn>
            <Btn ghost>↗ MANUAL INGEST</Btn>
            <Btn primary>RETRY ALL</Btn>
          </div>
        }
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden", padding: 16 }}>
          {lastIngest && (
            <div
              className="row gap-2"
              style={{
                alignItems: "center",
                padding: "8px 12px",
                marginBottom: 10,
                border: "1px solid var(--amber-dim)",
                background: "var(--bg-1)",
                fontSize: 11,
                color: "var(--ink-0)",
              }}
            >
              <Chip tone={lastIngest.status === "duplicate" ? "amber" : "green"}>
                {lastIngest.status.toUpperCase()}
              </Chip>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {lastIngest.status === "duplicate" ? "Already ingested: " : "Ingested: "}
                <strong>{lastIngest.title}</strong>{" "}
                <span className="muted">· {lastIngest.chars.toLocaleString()} chars</span>
              </span>
              <Btn ghost onClick={handleExtractClaims} style={{ fontSize: 9, padding: "3px 8px" }}>
                EXTRACT CLAIMS
              </Btn>
              <Btn ghost onClick={() => setLastIngest(null)} style={{ fontSize: 9, padding: "3px 8px" }}>
                ×
              </Btn>
            </div>
          )}
          {remote.isLoading ? (
            <Skeleton rows={6} rowHeight={64} gap={10} style={{ padding: 0 }} />
          ) : (sources ?? ARGUS_DATA.SOURCES).length === 0 ? (
            <EmptyState
              title="No sources ingested yet"
              hint="Click + INGEST URL above to add a source"
              cta={{ label: "+ INGEST URL", onClick: () => setModalOpen(true) }}
            />
          ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 10,
              overflowY: "auto",
              paddingRight: 4,
            }}
          >
            {(sources ?? ARGUS_DATA.SOURCES).map((s) => {
              const tone = s.status === "down" ? "red" : s.status === "warn" ? "amber" : "green";
              return (
                <div
                  key={s.id}
                  className="panel"
                  style={{
                    padding: 12,
                    borderColor:
                      tone === "red"
                        ? "var(--red-dim)"
                        : tone === "amber"
                          ? "var(--amber-dim)"
                          : "var(--line-2)",
                  }}
                >
                  <div className="row gap-2" style={{ alignItems: "center", marginBottom: 6 }}>
                    <Dot tone={tone} pulse={tone !== "green"} />
                    <span style={{ fontSize: 12, color: "var(--ink-0)", fontWeight: 600 }}>
                      {s.name}
                    </span>
                    <div style={{ flex: 1 }} />
                    <Chip>{s.type}</Chip>
                  </div>
                  <KV
                    k="Status"
                    v={s.status.toUpperCase()}
                    vColor={
                      tone === "red"
                        ? "var(--red)"
                        : tone === "amber"
                          ? "var(--amber)"
                          : "var(--green)"
                    }
                  />
                  <KV k="Latency" v={s.status === "down" ? "—" : `${s.latency}s`} />
                  <KV
                    k="Error rate"
                    v={s.status === "down" ? "100%" : `${(s.errorRate * 100).toFixed(2)}%`}
                  />
                  <KV k="Last update" v={`−${s.lastUpdate}`} />
                  <KV k="Quality" v={s.status === "down" ? "—" : s.quality.toFixed(2)} />
                  <KV k="Coverage" v={s.coverage} />
                  <div className="row gap-2" style={{ marginTop: 8 }}>
                    <Btn ghost style={{ flex: 1, fontSize: 9, padding: "3px 6px" }}>
                      {s.status === "down" ? "RETRY" : "PAUSE"}
                    </Btn>
                    <Btn ghost style={{ flex: 1, fontSize: 9, padding: "3px 6px" }}>
                      LOGS
                    </Btn>
                  </div>
                </div>
              );
            })}
          </div>
          )}
        </div>
        <div
          style={{
            width: 320,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          {(() => {
            const statsLive = stats.isSuccess && !!stats.data;
            const s = stats.data;
            const eventsPerHr = statsLive ? s!.events_per_hour_24h : null;
            const sparkData =
              statsLive && s!.spark_24h.length > 0
                ? s!.spark_24h
                : [1.2, 1.4, 1.6, 1.5, 1.8, 2.1, 2.4, 2.8, 3.0, 3.2, 3.4, 3.4];
            const total = statsLive ? s!.total : null;
            const last24h = statsLive ? s!.last_24h : null;
            const topPub = statsLive ? s!.by_publisher_top10[0] ?? null : null;
            const tier1Share =
              statsLive && s!.total > 0
                ? ((s!.by_trust_tier["1"] ?? 0) / s!.total) * 100
                : null;
            return (
              <Panel
                id="STATS"
                title="Aggregate"
                sub="all sources · 24h"
                right={<MockBadge online={statsLive} loading={stats.isLoading} />}
              >
                <div style={{ padding: 14 }}>
                  <div className="row gap-3">
                    <div style={{ flex: 1 }}>
                      <div className="tt-up muted" style={{ fontSize: 9 }}>
                        EVENTS / HR
                      </div>
                      <div
                        className="tab"
                        style={{ fontSize: 22, color: "var(--amber)", fontWeight: 600 }}
                      >
                        {eventsPerHr != null ? eventsPerHr.toFixed(2) : "3,418"}
                      </div>
                      <Sparkline data={sparkData} width={140} height={24} />
                    </div>
                  </div>
                  <div style={{ marginTop: 14 }}>
                    <KV
                      k="Total ingested"
                      v={total != null ? total.toLocaleString() : "2.41M"}
                    />
                    <KV
                      k="Last 24h"
                      v={last24h != null ? last24h.toLocaleString() : "—"}
                    />
                    <KV
                      k="Top publisher"
                      v={topPub ? `${topPub.name} · ${topPub.count}` : "—"}
                    />
                    <KV
                      k="Trust tier 1 share"
                      v={
                        tier1Share != null
                          ? `${tier1Share.toFixed(1)}%`
                          : "—"
                      }
                      vColor={tier1Share != null ? "var(--green)" : undefined}
                    />
                    <KV k="Avg latency p95" v={<span className="muted">— demo</span>} />
                  </div>
                </div>
              </Panel>
            );
          })()}
          <Panel
            id="MAP"
            title="Coverage Map"
            right={<Chip tone="amber">demo</Chip>}
          >
            <div style={{ padding: 14, fontSize: 10, color: "var(--ink-1)" }}>
              <div style={{ marginBottom: 4 }}>
                Indo-Pacific <span className="amber">▰▰▰▰▰▰▰▰▱▱</span> 81%
              </div>
              <div style={{ marginBottom: 4 }}>
                EU/UK <span className="amber">▰▰▰▰▰▰▰▱▱▱</span> 72%
              </div>
              <div style={{ marginBottom: 4 }}>
                Americas <span className="amber">▰▰▰▰▰▰▱▱▱▱</span> 64%
              </div>
              <div style={{ marginBottom: 4 }}>
                MENA <span className="amber">▰▰▰▰▱▱▱▱▱▱</span> 41%
              </div>
              <div style={{ marginBottom: 4 }}>
                Sub-Sah Africa <span className="amber">▰▰▰▱▱▱▱▱▱▱</span> 28%
              </div>
            </div>
          </Panel>
        </div>
      </div>
      <AddSourceModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onIngested={handleIngested}
      />
    </div>
  );
}
