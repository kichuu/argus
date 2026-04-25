"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { EmptyState } from "@/components/ui/EmptyState";
import { KV } from "@/components/ui/KV";
import { MockBadge } from "@/components/ui/MockBadge";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { Sparkline } from "@/components/ui/Sparkline";
import { api } from "@/lib/api";

// --- formatting helpers -------------------------------------------------------

function fmtCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function fmtMoney(n: number): string {
  return `$${n.toFixed(2)}`;
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function fmtPct(n: number | null | undefined, digits = 1): string {
  if (n == null) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

function fmtNumOrDash(n: number | null | undefined, digits = 2): string {
  if (n == null) return "—";
  return n.toFixed(digits);
}

function fmtLatency(s: number | null): string {
  if (s == null) return "—";
  return `${s.toFixed(1)}s`;
}

function statusColor(s: string): string {
  if (s === "ok" || s === "completed") return "var(--green)";
  if (s === "fail" || s === "failed") return "var(--red)";
  return "var(--amber)";
}

function evalToneColor(v: number | null): string {
  if (v == null) return "var(--ink-2)";
  if (v >= 0.8) return "var(--green)";
  if (v >= 0.6) return "var(--amber)";
  return "var(--red)";
}

// --- screen -------------------------------------------------------------------

export function ObsScreen() {
  const [range, setRange] = useState<"1h" | "24h" | "7d" | "30d">("24h");

  const overviewQ = useQuery({
    queryKey: ["metrics", "overview"],
    queryFn: api.metricsOverview,
    retry: 0,
    staleTime: 15_000,
  });

  const tracesQ = useQuery({
    queryKey: ["metrics", "traces"],
    queryFn: () => api.metricsTraces({ limit: 20 }),
    retry: 0,
    staleTime: 15_000,
  });

  const evalsQ = useQuery({
    queryKey: ["metrics", "evals"],
    queryFn: api.metricsEvals,
    retry: 0,
    staleTime: 60_000,
  });

  const live = overviewQ.isSuccess;
  const checking = overviewQ.isLoading;

  const ov = overviewQ.data;

  const kpis = [
    {
      lbl: "DEBATES 24H",
      v: ov ? fmtCount(ov.debates_24h) : "—",
      spark: ov?.spark_debates ?? [],
      c: "var(--amber)",
    },
    {
      lbl: "TOK 24H",
      v: ov ? fmtTokens(ov.tok_24h_est) : "—",
      spark: ov?.spark_claims ?? [],
      c: "var(--green)",
    },
    {
      lbl: "COST 24H",
      v: ov ? fmtMoney(ov.cost_24h_est_usd) : "—",
      spark: ov?.spark_cost ?? [],
      c: "var(--ink-0)",
    },
    {
      lbl: "ERR RATE",
      v: ov?.err_rate != null ? fmtPct(ov.err_rate, 1) : "—",
      spark: ov?.spark_err ?? [],
      c: "var(--red)",
    },
  ];

  const traces = tracesQ.data?.traces ?? [];
  const evals = evalsQ.data;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="12·OBS"
        title="Observability"
        breadcrumb="// phoenix · temporal · evals"
        right={
          <div className="row gap-2" style={{ alignItems: "center", gap: 8 }}>
            <MockBadge online={live} loading={checking} />
            <Segmented
              size="sm"
              options={["1h", "24h", "7d", "30d"] as const}
              value={range}
              onChange={(v) => setRange(v)}
            />
            <Btn ghost>↗ PHOENIX</Btn>
          </div>
        }
      />
      <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
            marginBottom: 16,
          }}
        >
          {kpis.map((s) => (
            <Panel key={s.lbl}>
              <div style={{ padding: 14 }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  {s.lbl}
                </div>
                <div className="tab" style={{ fontSize: 24, color: s.c, fontWeight: 600 }}>
                  {s.v}
                </div>
                {s.spark.length > 0 ? (
                  <Sparkline data={s.spark} width="100%" height={28} color={s.c} />
                ) : (
                  <div style={{ height: 28 }} />
                )}
              </div>
            </Panel>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Panel
            id="T"
            title="Traces"
            sub={`last ${traces.length} · phoenix`}
          >
            {traces.length === 0 ? (
              <div style={{ padding: 14 }}>
                <EmptyState
                  title="no traces yet"
                  hint="discussion runs will appear here once the first one is launched."
                />
              </div>
            ) : (
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Trace</th>
                    <th>Model</th>
                    <th>Tok</th>
                    <th>$</th>
                    <th>Lat</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {traces.map((r) => (
                    <tr key={r.id}>
                      <td className="tab muted">{`${r.id}·${r.label}`}</td>
                      <td>{r.model}</td>
                      <td className="tab">{fmtTokens(r.tokens_est)}</td>
                      <td className="tab">{fmtMoney(r.cost_est_usd)}</td>
                      <td className="tab">{fmtLatency(r.latency_seconds)}</td>
                      <td>
                        <span
                          style={{ color: statusColor(r.status) }}
                          className="tt-up"
                        >
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          <Panel
            id="W"
            title="Workflows"
            sub="temporal · running"
            right={<Chip tone="amber">demo</Chip>}
          >
            <div style={{ padding: 14, fontFamily: "JetBrains Mono", fontSize: 10, lineHeight: 1.7 }}>
              <div>
                <span className="green">▸</span> deliberation_v3 · d-2026-04-25-01 · turn 13/14 · running 1m 34s
              </div>
              <div>
                <span className="amber">▸</span> ingest_loop · running 14h 22m · 14k events
              </div>
              <div>
                <span className="amber">▸</span> kg_writer · running 14h 22m · queue 3
              </div>
              <div>
                <span className="green">✓</span> deliberation_v3 · d-2026-04-24-04 · 1m 41s
              </div>
              <div>
                <span className="green">✓</span> deliberation_v3 · d-2026-04-24-02 · 2m 08s
              </div>
              <div>
                <span className="red">✗</span> ingest_planet · 3 retries exceeded · 8h 42m ago
              </div>
              <div>
                <span className="green">✓</span> eval_consensus_quality · 47 debates · 4m 12s
              </div>
            </div>
          </Panel>

          <Panel
            id="P"
            title="Prompt Diffs"
            sub="auto-tuning history"
            right={<Chip tone="amber">demo</Chip>}
          >
            <div style={{ padding: 14, fontFamily: "JetBrains Mono", fontSize: 10, lineHeight: 1.7 }}>
              <div>
                <span className="muted">2026-04-24 18:02</span> · <span className="green">+0.04</span>{" "}
                consensus quality · orchestrator.cast_personas · v.42
              </div>
              <div>
                <span className="muted">2026-04-23 09:14</span> · <span className="green">+0.02</span>{" "}
                citation rate · persona.synthesize · v.31
              </div>
              <div>
                <span className="muted">2026-04-22 22:48</span> · <span className="red">−0.01</span> rolled
                back · persona.challenge · v.18
              </div>
              <div>
                <span className="muted">2026-04-21 11:30</span> · <span className="green">+0.06</span>{" "}
                minority capture · synthesizer · v.27
              </div>
            </div>
          </Panel>

          <Panel
            id="E"
            title="Evals"
            sub={
              evals?.last_run
                ? `last run · ${evals.last_run}${evals.n_gold != null ? ` · ${evals.n_gold} gold` : ""}`
                : "last run · —"
            }
          >
            <div style={{ padding: 14 }}>
              <KV
                k="Consensus quality"
                v={fmtNumOrDash(evals?.consensus_quality)}
                vColor={evalToneColor(evals?.consensus_quality ?? null)}
              />
              <KV
                k="Citation coverage"
                v={fmtNumOrDash(evals?.citation_coverage)}
                vColor={evalToneColor(evals?.citation_coverage ?? null)}
              />
              <KV
                k="Persona drift"
                v={fmtNumOrDash(evals?.persona_drift)}
                vColor={evalToneColor(evals?.persona_drift ?? null)}
              />
              <KV
                k="Synthesizer faithfulness"
                v={fmtNumOrDash(evals?.synth_faithfulness)}
                vColor={evalToneColor(evals?.synth_faithfulness ?? null)}
              />
              <KV
                k="Hallucination rate"
                v={fmtNumOrDash(evals?.hallucination_rate, 3)}
                vColor={
                  evals?.hallucination_rate == null
                    ? "var(--ink-2)"
                    : evals.hallucination_rate <= 0.05
                      ? "var(--green)"
                      : "var(--red)"
                }
              />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
