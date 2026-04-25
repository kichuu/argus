"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { useDebateStore } from "@/store/debate";

type LooseClaim = {
  id?: string;
  text?: string;
  subject?: string;
  predicate?: string;
  object?: string;
  confidence?: number;
  status?: string;
  source_id?: string;
};

export function SynthesisView() {
  const router = useRouter();
  const discussionId = useDebateStore((s) => s.discussionId);

  const liveClaims = useQuery({
    queryKey: ["discussion-claims", discussionId],
    queryFn: () => api.discussionClaims(discussionId as string),
    enabled: !!discussionId,
    retry: 0,
    staleTime: 30_000,
  });

  const messagesQuery = useQuery({
    queryKey: ["discussion-messages", discussionId],
    queryFn: () => api.discussionMessages(discussionId as string),
    enabled: !!discussionId,
    retry: 0,
    staleTime: 30_000,
  });

  const claims = (liveClaims.data ?? []) as LooseClaim[];
  const messages = messagesQuery.data ?? [];
  const isLive = !!discussionId && claims.length > 0;

  const dist = useMemo(() => {
    const buckets = { likely_true: 0, contested: 0, unverified: 0 };
    for (const c of claims) {
      const s = c.status;
      if (s === "likely_true") buckets.likely_true += 1;
      else if (s === "contested") buckets.contested += 1;
      else buckets.unverified += 1;
    }
    return buckets;
  }, [claims]);

  const meanConf = useMemo(() => {
    const vals = claims
      .map((c) => c.confidence)
      .filter((v): v is number => typeof v === "number" && !Number.isNaN(v));
    if (vals.length === 0) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }, [claims]);

  // Synthesizer summary: drawn from the latest "synthesis" / "summary" role
  // message in the message stream when available. No mock fallback.
  const synthMessage = useMemo(() => {
    const m = (messages as Array<{ role?: string; content?: string }>)
      .slice()
      .reverse()
      .find((x) => x.role === "synthesizer" || x.role === "synthesis" || x.role === "summary");
    return m?.content ?? null;
  }, [messages]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="07·SYNTH"
        title="Synthesis"
        breadcrumb={
          discussionId
            ? `// ${discussionId} · ${claims.length} claims · ${messages.length} messages`
            : "// no discussion selected"
        }
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            {isLive && <Chip tone="green">live · {claims.length} claims</Chip>}
            <Btn ghost>↗ EXPORT</Btn>
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
            {!discussionId ? (
              <EmptyState
                title="No discussion selected"
                hint="Open a debate from Library or launch one from Home."
                cta={{ label: "GO HOME", onClick: () => router.push("/") }}
              />
            ) : liveClaims.isError ? (
              <ErrorBox
                message="failed to load claims"
                onRetry={() => liveClaims.refetch()}
              />
            ) : (
              <>
                {synthMessage && (
                  <div
                    className="panel"
                    style={{ padding: 24, borderLeft: "3px solid var(--amber)" }}
                  >
                    <div
                      className="tt-up"
                      style={{ color: "var(--amber)", fontSize: 10, fontWeight: 600, marginBottom: 8 }}
                    >
                      SYNTHESIZER DIGEST
                    </div>
                    <p
                      className="t-serif"
                      style={{
                        fontSize: 16,
                        color: "var(--ink-0)",
                        lineHeight: 1.55,
                        margin: 0,
                        fontWeight: 400,
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {synthMessage}
                    </p>
                  </div>
                )}

                <Panel
                  id="E"
                  title="Evidence Trail"
                  sub={isLive ? `${claims.length} claims · live` : "—"}
                >
                  {liveClaims.isLoading ? (
                    <Skeleton rows={6} rowHeight={14} style={{ padding: 16 }} />
                  ) : claims.length === 0 ? (
                    <EmptyState
                      title="No claims yet"
                      hint="Claims appear as the debate progresses."
                      style={{ margin: 16 }}
                    />
                  ) : (
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
                                {" "}· conf {c.confidence.toFixed(2)}
                              </span>
                            )}
                            {c.status && (
                              <span
                                className="tt-up"
                                style={{
                                  marginLeft: 6,
                                  fontSize: 9,
                                  color:
                                    c.status === "likely_true"
                                      ? "var(--green)"
                                      : c.status === "contested"
                                        ? "var(--amber)"
                                        : "var(--red)",
                                }}
                              >
                                · {c.status}
                              </span>
                            )}
                            {c.source_id && (
                              <>
                                {" "}→ <span className="green">{c.source_id}</span>
                              </>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Panel>
              </>
            )}
          </div>

          <div className="col gap-4">
            <Panel id="P" title="Claim ledger" sub={isLive ? `${claims.length} claims` : "—"}>
              <div style={{ padding: 16 }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  MEAN CONFIDENCE
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
                  {meanConf == null ? "—" : meanConf.toFixed(2)}
                </div>
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
                      Scenario distribution {claims.length > 0 ? `· ${claims.length} claims` : ""}
                    </span>
                  </div>
                  {claims.length === 0 ? (
                    <div className="muted" style={{ fontSize: 10 }}>no claims</div>
                  ) : (
                    [
                      { lbl: "Likely true", n: dist.likely_true, color: "var(--green)" },
                      { lbl: "Contested", n: dist.contested, color: "var(--amber)" },
                      { lbl: "Unverified", n: dist.unverified, color: "var(--red)" },
                    ].map((r) => {
                      const p = claims.length === 0 ? 0 : r.n / claims.length;
                      return (
                        <div
                          key={r.lbl}
                          className="row gap-2"
                          style={{ alignItems: "center", padding: "3px 0" }}
                        >
                          <span
                            className="tt-up"
                            style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 80 }}
                          >
                            {r.lbl}
                          </span>
                          <Bar value={p} max={1} width={120} color={r.color} />
                          <span
                            className="tab"
                            style={{ fontSize: 10, color: "var(--ink-1)" }}
                          >
                            {r.n}
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}
