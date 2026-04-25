"use client";
import { useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { KV } from "@/components/ui/KV";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { ARGUS_DATA, type KGEntity } from "@/mock/data";

const W = 800;
const H = 600;

const TYPE_COLOR: Record<string, string> = {
  country: "var(--p-1)",
  person: "var(--p-2)",
  company: "var(--p-4)",
  org: "var(--p-3)",
  event: "var(--p-5)",
  doc: "var(--p-6)",
  asset: "var(--p-7)",
  place: "var(--ink-1)",
};

const FILTERS = ["all", "country", "person", "org", "company", "event", "place", "doc", "asset"] as const;

export function KGScreen() {
  const D = ARGUS_DATA;
  const [sel, setSel] = useState<KGEntity | null>(
    D.KG_ENTITIES.find((e) => e.id === "tw") ?? D.KG_ENTITIES[0],
  );
  const [filter, setFilter] = useState<string>("all");

  const ents = filter === "all" ? D.KG_ENTITIES : D.KG_ENTITIES.filter((e) => e.type === filter);
  const entIds = new Set(ents.map((e) => e.id));
  const edges = D.KG_EDGES.filter(([a, b]) => entIds.has(a) && entIds.has(b));

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="03·KG"
        title="Knowledge Graph Explorer"
        breadcrumb={`// ${D.KG_ENTITIES.length} entities · ${D.KG_EDGES.length} edges · v.t = 14:22:08Z`}
        right={
          <div className="row gap-2">
            <Segmented size="sm" options={FILTERS} value={filter} onChange={setFilter} />
            <Btn ghost>◐ EMBEDDINGS</Btn>
            <Btn ghost>↗ EXPORT</Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          className="grow grid-bg"
          style={{ position: "relative", overflow: "hidden", background: "var(--bg-1)" }}
        >
          <svg
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: "100%", height: "100%" }}
            preserveAspectRatio="xMidYMid meet"
          >
            {edges.map(([a, b, rel], i) => {
              const ea = D.KG_ENTITIES.find((e) => e.id === a);
              const eb = D.KG_ENTITIES.find((e) => e.id === b);
              if (!ea || !eb) return null;
              const x1 = ea.x * W;
              const y1 = ea.y * H;
              const x2 = eb.x * W;
              const y2 = eb.y * H;
              const isSel = sel && (sel.id === a || sel.id === b);
              return (
                <g key={i}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={isSel ? "var(--amber)" : "var(--line-2)"}
                    strokeWidth={isSel ? 1 : 0.5}
                    opacity={isSel ? 0.9 : 0.5}
                  />
                  {isSel && (
                    <text
                      x={(x1 + x2) / 2}
                      y={(y1 + y2) / 2 - 3}
                      fontSize="8"
                      fill="var(--amber)"
                      fontFamily="JetBrains Mono"
                      textAnchor="middle"
                    >
                      {rel}
                    </text>
                  )}
                </g>
              );
            })}
            {ents.map((e) => {
              const cx = e.x * W;
              const cy = e.y * H;
              const isSel = sel?.id === e.id;
              const r = 4 + Math.sqrt(e.deg) * 1.5;
              const c = TYPE_COLOR[e.type] || "var(--ink-1)";
              return (
                <g key={e.id} style={{ cursor: "pointer" }} onClick={() => setSel(e)}>
                  {isSel && <circle cx={cx} cy={cy} r={r + 8} fill={c} opacity="0.18" />}
                  <circle
                    cx={cx}
                    cy={cy}
                    r={r}
                    fill="var(--bg-1)"
                    stroke={c}
                    strokeWidth={isSel ? 2 : 1}
                  />
                  <circle cx={cx} cy={cy} r={r / 2} fill={c} />
                  <text
                    x={cx + r + 5}
                    y={cy + 3}
                    fontSize="9"
                    fill={isSel ? "var(--ink-0)" : "var(--ink-1)"}
                    fontFamily="JetBrains Mono"
                  >
                    {e.label}
                  </text>
                </g>
              );
            })}
            <text x={10} y={18} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">
              FORCE-DIRECTED · t-SNE COMPONENTS · CONFIDENCE OVERLAY OFF
            </text>
          </svg>

          <div
            style={{
              position: "absolute",
              bottom: 12,
              left: 12,
              background: "var(--bg-2)",
              border: "1px solid var(--line-2)",
              padding: "6px 10px",
              display: "flex",
              gap: 12,
              fontSize: 9,
            }}
          >
            {Object.entries(TYPE_COLOR).map(([k, c]) => (
              <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <span
                  style={{ width: 6, height: 6, borderRadius: "50%", background: c }}
                />{" "}
                <span className="tt-up" style={{ color: "var(--ink-2)" }}>
                  {k}
                </span>
              </span>
            ))}
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
          {sel && (
            <>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                  {sel.type}
                </div>
                <div
                  style={{
                    fontSize: 16,
                    color: "var(--ink-0)",
                    marginTop: 2,
                    fontWeight: 600,
                  }}
                >
                  {sel.label}
                </div>
                <div className="row gap-2" style={{ marginTop: 8 }}>
                  <Chip tone="amber">deg {sel.deg}</Chip>
                  <Chip>conf 0.91</Chip>
                </div>
              </div>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                >
                  HISTORY · validity windows
                </div>
                {[
                  { t: "2024-05-20", e: "Lai Ching-te inaugurated" },
                  { t: "2025-01-04", e: "Conscription extended to 1y" },
                  { t: "2026-03-11", e: "Hai Kun commissioned" },
                  { t: "2026-04-22", e: "Joint Sword 2026-A response" },
                ].map((h, i) => (
                  <div
                    key={i}
                    className="row gap-3"
                    style={{ padding: "4px 0", fontSize: 10 }}
                  >
                    <span className="tab muted" style={{ minWidth: 70 }}>
                      {h.t}
                    </span>
                    <span style={{ color: "var(--ink-1)" }}>{h.e}</span>
                  </div>
                ))}
              </div>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                >
                  LINKED DEBATES (3)
                </div>
                {D.RECENT.slice(0, 3).map((d) => (
                  <div
                    key={d.id}
                    style={{ padding: "4px 0", fontSize: 11, color: "var(--ink-1)" }}
                  >
                    · {d.title}
                  </div>
                ))}
              </div>
              <div style={{ padding: 14 }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                >
                  TOP CITATIONS
                </div>
                <KV k="Reuters" v="412" />
                <KV k="GDELT" v="289" />
                <KV k="Xinhua" v="178" />
                <KV k="CSIS" v="44" />
              </div>
            </>
          )}
        </div>
      </div>

      <div
        style={{
          height: 36,
          borderTop: "1px solid var(--line-2)",
          background: "var(--bg-1)",
          display: "flex",
          alignItems: "center",
          padding: "0 12px",
          gap: 12,
          flexShrink: 0,
        }}
      >
        <Btn ghost>◀ −1h</Btn>
        <span className="muted tt-up" style={{ fontSize: 9 }}>
          2024-01
        </span>
        <div style={{ flex: 1, height: 4, background: "var(--bg-3)" }}>
          <div style={{ width: "92%", height: "100%", background: "var(--amber)" }} />
        </div>
        <span className="muted tt-up" style={{ fontSize: 9 }}>
          NOW
        </span>
        <Btn ghost>+1h ▶</Btn>
      </div>
    </div>
  );
}
