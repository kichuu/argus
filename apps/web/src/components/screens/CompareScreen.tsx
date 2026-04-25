"use client";
import { Bar } from "@/components/ui/Bar";
import { Chip } from "@/components/ui/Chip";
import { ScreenHeader } from "@/components/ui/ScreenHeader";

const ROWS = [
  { title: "Apr 25, 2026", quar: 0.42, blo: 0.18, kin: 0.07, status: "current", color: "var(--amber)" },
  { title: "Mar 22, 2026", quar: 0.31, blo: 0.14, kin: 0.05, status: "month ago", color: "var(--p-2)" },
] as const;

export function CompareScreen() {
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="10·COMPARE"
        title="Compare Mode"
        breadcrumb="// 2 debates · TW Strait Apr-25 vs TW Strait Mar-22"
      />
      <div className="grow row" style={{ overflow: "hidden" }}>
        {ROWS.map((d, i) => (
          <div
            key={i}
            className="grow col"
            style={{
              borderRight: i === 0 ? "1px solid var(--line-2)" : "none",
              padding: 24,
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
              {(
                [
                  ["Quarantine", d.quar],
                  ["Blockade", d.blo],
                  ["Kinetic", d.kin],
                  ["Status quo", 1 - d.quar - d.blo - d.kin],
                ] as const
              ).map(([l, p]) => (
                <div
                  key={l}
                  className="row gap-2"
                  style={{ alignItems: "center", padding: "4px 0" }}
                >
                  <span
                    className="tt-up"
                    style={{
                      fontSize: 9,
                      color: "var(--ink-2)",
                      minWidth: 90,
                    }}
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
        ))}
      </div>
    </div>
  );
}
