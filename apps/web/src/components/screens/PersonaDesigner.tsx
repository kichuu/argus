"use client";
import { useState } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { KV } from "@/components/ui/KV";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { ARGUS_DATA, type Persona } from "@/mock/data";

function SliderRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ padding: "5px 0" }}>
      <div className="row gap-2" style={{ alignItems: "center" }}>
        <span
          className="tt-up"
          style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 110 }}
        >
          {label}
        </span>
        <div
          style={{
            flex: 1,
            height: 4,
            background: "var(--bg-3)",
            border: "1px solid var(--line-1)",
            position: "relative",
          }}
        >
          <div style={{ width: `${value * 100}%`, height: "100%", background: color }} />
          <div
            style={{
              position: "absolute",
              left: `${value * 100}%`,
              top: -3,
              width: 2,
              height: 10,
              background: "var(--ink-0)",
              transform: "translateX(-1px)",
            }}
          />
        </div>
        <span
          className="tab"
          style={{ fontSize: 10, color: "var(--ink-1)", minWidth: 32, textAlign: "right" }}
        >
          {value.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

export function PersonaDesigner() {
  const D = ARGUS_DATA;
  const [sel, setSel] = useState<Persona>(D.PERSONAS[0]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="05·PERSONAS"
        title="Persona Designer"
        breadcrumb="// 7 cast · auto-balance enabled"
        right={
          <div className="row gap-2">
            <Btn ghost>+ ADD PERSONA</Btn>
            <Btn ghost>◫ TEMPLATE LIBRARY</Btn>
            <Btn ghost>◐ AUTO-BALANCE</Btn>
            <Btn primary>SAVE CAST →</Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden", padding: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: 12,
              overflowY: "auto",
              paddingRight: 4,
            }}
          >
            {D.PERSONAS.map((p) => {
              const isSel = sel.id === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setSel(p)}
                  className={`panel bd-${p.color}`}
                  style={{
                    padding: 14,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                    borderColor: isSel ? p.colorVar : "var(--line-2)",
                    borderWidth: isSel ? 2 : 1,
                    borderStyle: "solid",
                    background: isSel ? "var(--bg-3)" : "var(--bg-2)",
                  }}
                >
                  <div className="row gap-3" style={{ alignItems: "flex-start" }}>
                    <PersonaAvatar p={p} size={42} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600 }}
                      >
                        {p.name}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--ink-1)" }}>{p.role}</div>
                      <div
                        className="tt-up"
                        style={{ fontSize: 9, color: p.colorVar, marginTop: 2 }}
                      >
                        {p.flag} {p.country} · {p.model}
                      </div>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--ink-3)", cursor: "pointer" }}>
                      ⋯
                    </span>
                  </div>
                  <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
                    BIAS
                  </div>
                  <div style={{ fontSize: 11, color: "var(--ink-1)", lineHeight: 1.4 }}>
                    {p.bias}
                  </div>
                  <div className="row gap-3">
                    <div style={{ flex: 1 }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                        TEMP
                      </span>
                      <Bar value={p.temperature} color={p.colorVar} width="100%" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                        AGGR
                      </span>
                      <Bar value={p.aggression} color="var(--red)" width="100%" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                        CITE
                      </span>
                      <Bar value={p.citationStrictness} color="var(--green)" width="100%" />
                    </div>
                  </div>
                  <div className="row gap-2">
                    {p.beliefs.slice(0, 2).map((b, i) => (
                      <Chip key={i}>{b}</Chip>
                    ))}
                  </div>
                </div>
              );
            })}
            <div
              style={{
                border: "1px dashed var(--line-3)",
                padding: 14,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--ink-3)",
                fontSize: 11,
                minHeight: 200,
                cursor: "pointer",
              }}
            >
              <div style={{ fontSize: 22, marginBottom: 8 }}>+</div>
              <div className="tt-up">ADD PERSONA</div>
              <div style={{ fontSize: 10, marginTop: 4, textAlign: "center" }}>
                auto-balance suggests:
                <br />
                <span style={{ color: "var(--amber)" }}>EU diplomat · KR security analyst</span>
              </div>
            </div>
          </div>
        </div>

        <div
          className="col"
          style={{
            width: 380,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          <div
            style={{
              padding: 16,
              borderBottom: "1px solid var(--line-2)",
              background: "var(--bg-2)",
            }}
          >
            <div className="row gap-3" style={{ alignItems: "flex-start" }}>
              <PersonaAvatar p={sel} size={48} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{ fontSize: 16, color: "var(--ink-0)", fontWeight: 600 }}
                >
                  {sel.name}
                </div>
                <div style={{ fontSize: 11, color: "var(--ink-1)" }}>{sel.role}</div>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: sel.colorVar, marginTop: 4 }}
                >
                  {sel.flag} {sel.country}
                </div>
              </div>
            </div>
          </div>

          <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}
            >
              SYSTEM PROMPT · 1.4k tok
            </div>
            <div
              style={{
                background: "var(--bg-0)",
                padding: 10,
                fontSize: 10,
                fontFamily: "JetBrains Mono",
                color: "var(--ink-1)",
                lineHeight: 1.5,
                border: "1px solid var(--line-1)",
                maxHeight: 150,
                overflowY: "auto",
              }}
            >
              You are <span style={{ color: sel.colorVar }}>{sel.name}</span>, {sel.role}. Speak
              from this position with the tone, priorities, and constraints the role implies.
              Reference your stated beliefs. When you cite, prefer primary sources from your
              nation/institution. You may reference the shared world state but must hold your own
              institutional memory. Constitution: {sel.redlines.length} red-line
              {sel.redlines.length === 1 ? "" : "s"} enforced.
            </div>
            <Btn ghost style={{ marginTop: 8 }}>
              EDIT PROMPT
            </Btn>
          </div>

          <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}
            >
              BELIEFS
            </div>
            {sel.beliefs.map((b, i) => (
              <div
                key={i}
                style={{
                  padding: "4px 0",
                  fontSize: 11,
                  color: "var(--ink-1)",
                  display: "flex",
                  gap: 6,
                }}
              >
                <span style={{ color: sel.colorVar }}>·</span>
                <span style={{ flex: 1 }}>{b}</span>
              </div>
            ))}
          </div>

          <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--red)", marginBottom: 8 }}
            >
              RED LINES · constitution
            </div>
            {sel.redlines.length === 0 ? (
              <div className="muted" style={{ fontSize: 10 }}>
                none — observer persona
              </div>
            ) : (
              sel.redlines.map((r, i) => (
                <div
                  key={i}
                  style={{ padding: "4px 0", fontSize: 11, color: "var(--ink-1)" }}
                >
                  ⊘ {r}
                </div>
              ))
            )}
          </div>

          <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}
            >
              TUNING
            </div>
            <SliderRow label="Temperature" value={sel.temperature} color={sel.colorVar} />
            <SliderRow label="Aggression" value={sel.aggression} color="var(--red)" />
            <SliderRow
              label="Citation strict."
              value={sel.citationStrictness}
              color="var(--green)"
            />
          </div>

          <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}
            >
              TOOL ACCESS
            </div>
            {(
              [
                ["kg.search", true],
                ["kg.path", true],
                ["search.web", true],
                ["memory.read", true],
                ["memory.write", true],
                ["summon.persona", false],
              ] as const
            ).map(([t, on], i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "3px 0",
                  fontSize: 11,
                }}
              >
                <span style={{ color: on ? "var(--green)" : "var(--ink-3)" }}>
                  {on ? "■" : "□"}
                </span>
                <span style={{ color: on ? "var(--ink-0)" : "var(--ink-3)" }}>{t}</span>
              </div>
            ))}
          </div>

          <div style={{ padding: 14 }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
            >
              MEMORY · {sel.memorySize}
            </div>
            <KV k="Persistence" v="across-debate" />
            <KV k="Embeddings" v="text-3-large" />
            <KV k="Decay" v="exp(−t/30d)" />
          </div>
        </div>
      </div>
    </div>
  );
}
