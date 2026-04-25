"use client";
import { useQuery } from "@tanstack/react-query";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Sparkline } from "@/components/ui/Sparkline";
import { api } from "@/lib/api";
import { ARGUS_DATA } from "@/mock/data";

export function SourcesScreen() {
  const remote = useQuery({
    queryKey: ["sources"],
    queryFn: api.sources,
    retry: 0,
    staleTime: 30_000,
  });

  const sources = remote.data && remote.data.length > 0 ? null : ARGUS_DATA.SOURCES;
  const apiOnline = remote.isSuccess && (remote.data?.length ?? 0) > 0;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="11·SOURCES"
        title="Source Monitor"
        breadcrumb={`// ${apiOnline ? remote.data!.length : ARGUS_DATA.SOURCES.length} sources · ${apiOnline ? "live" : "mock"}`}
        right={
          <div className="row gap-2">
            <Btn ghost>+ ADD RSS</Btn>
            <Btn ghost>↗ MANUAL INGEST</Btn>
            <Btn primary>RETRY ALL</Btn>
          </div>
        }
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden", padding: 16 }}>
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
        </div>
        <div
          style={{
            width: 320,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          <Panel id="STATS" title="Aggregate" sub="all sources · 24h">
            <div style={{ padding: 14 }}>
              <div className="row gap-3">
                <div style={{ flex: 1 }}>
                  <div className="tt-up muted" style={{ fontSize: 9 }}>
                    EVENTS / HR
                  </div>
                  <div className="tab" style={{ fontSize: 22, color: "var(--amber)", fontWeight: 600 }}>
                    3,418
                  </div>
                  <Sparkline
                    data={[1.2, 1.4, 1.6, 1.5, 1.8, 2.1, 2.4, 2.8, 3.0, 3.2, 3.4, 3.4]}
                    width={140}
                    height={24}
                  />
                </div>
              </div>
              <div style={{ marginTop: 14 }}>
                <KV k="Total ingested" v="2.41M" />
                <KV k="Geocoded" v="98.2%" vColor="var(--green)" />
                <KV k="Deduped" v="−18.4%" />
                <KV k="Avg latency p95" v="2.1s" />
              </div>
            </div>
          </Panel>
          <Panel id="MAP" title="Coverage Map">
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
    </div>
  );
}
