"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { Sparkline } from "@/components/ui/Sparkline";
import { api } from "@/lib/api";
import { ARGUS_DATA } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

export function SynthesisView() {
  const router = useRouter();
  const D = ARGUS_DATA;
  const S = D.SYNTHESIS;
  const pById = (id: string) => D.PERSONAS.find((p) => p.id === id);
  const discussionId = useDebateStore((s) => s.discussionId);

  const liveClaims = useQuery({
    queryKey: ["discussion-claims", discussionId],
    queryFn: () => api.discussionClaims(discussionId as string),
    enabled: !!discussionId,
    retry: 0,
    staleTime: 30_000,
  });

  const claims = liveClaims.data ?? [];
  const isLive = !!discussionId && claims.length > 0;
  const showMockChip = !discussionId || liveClaims.isError || claims.length === 0;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="07·SYNTH"
        title="Synthesis"
        breadcrumb={
          isLive
            ? `// ${discussionId} · ${claims.length} claims (live)`
            : `// d-2026-04-25-01 · 7 personas · 13 turns · 1m 42s · ${S.evidence} citations`
        }
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {showMockChip && <Chip tone="amber">offline · mock</Chip>}
            {isLive && <Chip tone="green">live · {claims.length} claims</Chip>}
            <Btn ghost>↺ RE-RUN</Btn>
            <Btn ghost>⌥ COUNTERFACTUAL</Btn>
            <Btn ghost>↗ EXPORT</Btn>
            <Btn ghost>⎘ SHARE</Btn>
            <Btn primary>+ SUBSCRIBE</Btn>
          </div>
        }
      />

      <div className="grow" style={{ overflowY: "auto" }}>
        <div
          style={{
            maxWidth: 1280,
            margin: "0 auto",
            padding: 24,
            display: "grid",
            gridTemplateColumns: "1fr 360px",
            gap: 20,
          }}
        >
          <div className="col gap-4">
            <div className="panel" style={{ padding: 24, borderLeft: "3px solid var(--amber)" }}>
              <div
                className="row gap-2"
                style={{ alignItems: "center", marginBottom: 8 }}
              >
                <span
                  className="tt-up"
                  style={{ color: "var(--amber)", fontSize: 10, fontWeight: 600 }}
                >
                  CONSENSUS · 4 of 7 personas
                </span>
                <div style={{ flex: 1 }} />
                <Bar
                  value={S.confidence}
                  label="CONFIDENCE"
                  width={100}
                  color="var(--amber)"
                  showVal
                />
              </div>
              <p
                className="t-serif"
                style={{
                  fontSize: 18,
                  color: "var(--ink-0)",
                  lineHeight: 1.55,
                  margin: 0,
                  fontWeight: 400,
                }}
              >
                {S.consensus}
              </p>
              <div className="row gap-2" style={{ marginTop: 14 }}>
                {S.consensusFrom.map((id) => {
                  const p = pById(id);
                  if (!p) return null;
                  return (
                    <Chip key={id} style={{ borderColor: p.colorVar, color: p.colorVar }}>
                      {p.initials} {p.name.split(" ").slice(-1)}
                    </Chip>
                  );
                })}
              </div>
            </div>

            <Panel id="D" title="Dissent" sub={`${S.dissent.length} dissenting positions`}>
              <div className="col">
                {S.dissent.map((d, i) => {
                  const p = pById(d.from);
                  if (!p) return null;
                  return (
                    <div
                      key={i}
                      style={{
                        padding: 16,
                        borderBottom: "1px solid var(--line-1)",
                        display: "flex",
                        gap: 12,
                        alignItems: "flex-start",
                      }}
                    >
                      <PersonaAvatar p={p} size={32} />
                      <div style={{ flex: 1 }}>
                        <div className="row gap-2" style={{ alignItems: "baseline" }}>
                          <span
                            style={{ color: p.colorVar, fontWeight: 600, fontSize: 12 }}
                          >
                            {p.name}
                          </span>
                          <span className="muted" style={{ fontSize: 10 }}>
                            · {p.role}
                          </span>
                        </div>
                        <p
                          className="t-serif"
                          style={{
                            fontSize: 14,
                            color: "var(--ink-1)",
                            margin: "6px 0 0",
                            lineHeight: 1.5,
                          }}
                        >
                          {d.point}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>

            <Panel id="M" title="Minority Report" sub="single-source, high-leverage">
              <div style={{ padding: 16 }}>
                <p
                  className="t-serif"
                  style={{
                    fontSize: 14,
                    color: "var(--ink-1)",
                    margin: 0,
                    lineHeight: 1.55,
                    fontStyle: "italic",
                  }}
                >
                  &ldquo;{S.minority}&rdquo;
                </p>
              </div>
            </Panel>

            <Panel
              id="E"
              title="Evidence Trail"
              sub={
                isLive
                  ? `${claims.length} claims · live`
                  : `${S.evidence} citations · 9 sources · 14 KG nodes`
              }
            >
              {!discussionId ? (
                <EmptyState
                  title="No discussion selected"
                  hint="Open a debate from Library or launch one from Home to see its evidence trail"
                  cta={{ label: "GO HOME", onClick: () => router.push("/") }}
                  style={{ margin: 16 }}
                />
              ) : liveClaims.isLoading ? (
                <Skeleton rows={6} rowHeight={14} style={{ padding: 16 }} />
              ) : liveClaims.isError ? (
                <ErrorBox
                  message="failed to load claim ledger"
                  onRetry={() => liveClaims.refetch()}
                  style={{ margin: 16 }}
                />
              ) : isLive ? (
                <div style={{ padding: 16, fontSize: 11, lineHeight: 1.7 }}>
                  <div className="t-mono" style={{ color: "var(--ink-1)" }}>
                    {claims.map((c, i) => (
                      <div key={c.id ?? i}>
                        <span className="amber">
                          claim {String(i + 1).padStart(2, "0")}
                        </span>{" "}
                        &quot;
                        {c.text ??
                          [c.subject, c.predicate, c.object].filter(Boolean).join(" ") ??
                          c.id}
                        &quot;
                        {typeof c.confidence === "number" && (
                          <span className="muted">
                            {" "}
                            · conf {c.confidence.toFixed(2)}
                          </span>
                        )}
                        {c.source_id && (
                          <>
                            {" "}
                            → <span className="green">{c.source_id}</span>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
              <div style={{ padding: 16, fontSize: 11, lineHeight: 1.7 }}>
                <div className="t-mono" style={{ color: "var(--ink-1)" }}>
                  <div>
                    <span className="amber">claim 01</span> &quot;Joint Sword 2026-A concluded 78
                    hours ago&quot; → <span className="green">GDELT/PLA-EX-2026-04</span> →{" "}
                    <span className="cyan">kg.event(ja-sword)</span>
                  </div>
                  <div>
                    <span className="amber">claim 02</span> &quot;2005 Anti-Secession Law authorizes
                    non-peaceful means&quot; →{" "}
                    <span className="green">Xinhua/Anti-Secession Law Art.8</span> →{" "}
                    <span className="cyan">kg.doc(asl)</span>
                  </div>
                  <div>
                    <span className="amber">claim 03</span> &quot;ROCS Hai Kun commissioned
                    2026-03-11&quot; → <span className="green">Reuters/Hai Kun</span> →{" "}
                    <span className="cyan">kg.asset(haikun)</span>
                  </div>
                  <div>
                    <span className="amber">claim 04</span> &quot;INDOPACOM munitions flow within
                    96h&quot; → <span className="green">DoD/Indo-Pacific Strategy 2025</span>
                  </div>
                  <div>
                    <span className="amber">claim 05</span> &quot;TSMC Arizona N4P at ~20% TW
                    capacity&quot; → <span className="green">TSMC IR Q1 2026</span> →{" "}
                    <span className="cyan">kg.asset(fab21)</span>
                  </div>
                  <div>
                    <span className="amber">claim 06</span> &quot;2022 NSS reinterpretation&quot; →{" "}
                    <span className="green">MOFA-JP/NSS 2022</span> →{" "}
                    <span className="cyan">kg.doc(nss22)</span>
                  </div>
                  <div>
                    <span className="amber">claim 07</span> &quot;ESC-TW April 2026 poll: 72%
                    status quo&quot; → <span className="green">ESC-TW/n=1247</span>
                  </div>
                  <div className="muted">... 10 more claims, fully cited ...</div>
                </div>
              </div>
              )}
            </Panel>

            <Panel id="O" title="Open Questions" sub="unresolved · synthesizer-flagged">
              <div style={{ padding: 8 }}>
                {S.open.map((q, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "10px 12px",
                      borderBottom: i < S.open.length - 1 ? "1px solid var(--line-1)" : "none",
                      display: "flex",
                      gap: 10,
                      alignItems: "flex-start",
                    }}
                  >
                    <span className="tab amber" style={{ fontSize: 10 }}>
                      Q{String(i + 1).padStart(2, "0")}
                    </span>
                    <span
                      style={{
                        flex: 1,
                        fontSize: 12,
                        color: "var(--ink-1)",
                        lineHeight: 1.5,
                      }}
                    >
                      {q}
                    </span>
                    <Btn ghost style={{ fontSize: 9 }}>
                      ↺ RE-RUN
                    </Btn>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <div className="col gap-4">
            <Panel id="P" title="Probability">
              <div style={{ padding: 16 }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  QUARANTINE · 12mo
                </div>
                <div
                  className="tab"
                  style={{
                    fontSize: 42,
                    color: "var(--amber)",
                    fontWeight: 600,
                    lineHeight: 1,
                    margin: "4px 0",
                  }}
                >
                  0.42
                </div>
                <div className="row gap-2" style={{ alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: 10 }}>
                    ±0.13
                  </span>
                  <Sparkline
                    data={[0.18, 0.22, 0.28, 0.31, 0.35, 0.39, 0.42]}
                    width={120}
                    height={20}
                    fill
                  />
                </div>
                {(() => {
                  const buckets = { likely_true: 0, contested: 0, unverified: 0 };
                  for (const c of claims) {
                    const st = (c as { status?: string }).status;
                    if (st === "likely_true") buckets.likely_true += 1;
                    else if (st === "contested") buckets.contested += 1;
                    else buckets.unverified += 1;
                  }
                  const n = claims.length;
                  const distLive = isLive && n > 0;
                  const rows = distLive
                    ? [
                        {
                          lbl: "Likely true",
                          p: buckets.likely_true / n,
                          color: "var(--green)",
                        },
                        {
                          lbl: "Contested",
                          p: buckets.contested / n,
                          color: "var(--amber)",
                        },
                        {
                          lbl: "Unverified",
                          p: buckets.unverified / n,
                          color: "var(--red)",
                        },
                      ]
                    : [
                        { lbl: "Quarantine", p: 0.42, color: "var(--amber)" },
                        { lbl: "Blockade", p: 0.18, color: "var(--red)" },
                        { lbl: "Kinetic", p: 0.07, color: "var(--red)" },
                        { lbl: "Status quo", p: 0.33, color: "var(--green)" },
                      ];
                  return (
                    <div
                      style={{
                        marginTop: 14,
                        paddingTop: 12,
                        borderTop: "1px solid var(--line-1)",
                      }}
                    >
                      <div
                        className="row gap-2"
                        style={{ alignItems: "center", marginBottom: 6 }}
                      >
                        <span
                          className="tt-up muted"
                          style={{ fontSize: 9, flex: 1 }}
                        >
                          Scenario distribution{" "}
                          {distLive ? `· ${n} claims` : ""}
                        </span>
                        {!distLive && <Chip tone="amber">mock</Chip>}
                      </div>
                      {rows.map((r) => (
                        <div
                          key={r.lbl}
                          className="row gap-2"
                          style={{ alignItems: "center", padding: "3px 0" }}
                        >
                          <span
                            className="tt-up"
                            style={{
                              fontSize: 9,
                              color: "var(--ink-2)",
                              minWidth: 80,
                            }}
                          >
                            {r.lbl}
                          </span>
                          <Bar value={r.p} max={1} width={120} color={r.color} />
                          <span
                            className="tab"
                            style={{ fontSize: 10, color: "var(--ink-1)" }}
                          >
                            {r.p.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </Panel>

            <Panel id="X" title="Counterfactuals">
              <div style={{ padding: 12 }}>
                {S.counterfactuals.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "8px 0",
                      borderBottom:
                        i < S.counterfactuals.length - 1 ? "1px solid var(--line-1)" : "none",
                    }}
                  >
                    <div
                      style={{ fontSize: 11, color: "var(--ink-0)", fontWeight: 500 }}
                    >
                      {c.name}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--ink-2)", marginTop: 2 }}>
                      {c.impact}
                    </div>
                  </div>
                ))}
                <Btn ghost style={{ marginTop: 8, width: "100%" }}>
                  + TEST COUNTERFACTUAL
                </Btn>
              </div>
            </Panel>

            <Panel id="A" title="Anchored to">
              <div style={{ padding: 12 }}>
                <KV k="WorldView pin" v="e1 · TW Strait" />
                <KV k="KG entity" v="tw / cn / pla" />
                <KV k="Time anchor" v="2026-04-25 14:22Z" />
                <KV k="Source" v="GDELT · PLA-EX-2026-04" />
              </div>
            </Panel>

            <Panel id="L" title="Lineage">
              <div style={{ padding: 12, fontSize: 10, color: "var(--ink-1)" }}>
                <div>↳ d-2026-04-15-03 (TW preparedness)</div>
                <div>↳ d-2026-03-22-01 (PLA exercise patterns)</div>
                <div>↳ d-2026-02-08-02 (TWD/USD scenarios)</div>
                <Btn ghost style={{ marginTop: 8 }}>
                  ↗ DIFF WITH PARENT
                </Btn>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}
