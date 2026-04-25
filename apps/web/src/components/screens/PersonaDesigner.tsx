"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { KV } from "@/components/ui/KV";
import { MockBadge } from "@/components/ui/MockBadge";
import { PersonaAvatar } from "@/components/ui/PersonaAvatar";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type PersonaSummary } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";
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
  const qc = useQueryClient();
  const [sel, setSel] = useState<Persona>(D.PERSONAS[0]);
  const [savedSel, setSavedSel] = useState<string | null>(null);
  const [draftFrame, setDraftFrame] = useState<string>(D.PERSONAS[0].role);
  const [draftDescription, setDraftDescription] = useState<string>(D.PERSONAS[0].bias);
  const [draftEmphasis, setDraftEmphasis] = useState<string>(
    D.PERSONAS[0].beliefs.join(", "),
  );

  const personasQuery = useQuery({
    queryKey: ["personas"],
    queryFn: api.personas,
    retry: 0,
    staleTime: 30_000,
  });

  const status = apiStatus(personasQuery);
  const apiOnline = status.online;

  const savedPersonas: PersonaSummary[] = useMemo(
    () => (apiOnline && personasQuery.data ? personasQuery.data : []),
    [apiOnline, personasQuery.data],
  );

  const createMutation = useMutation({
    mutationFn: (body: { frame: string; description: string; knowledge_emphasis: string[] }) =>
      api.createPersona(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePersona(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });

  // When a persona is loaded into the designer from the saved list, sync drafts.
  useEffect(() => {
    if (!savedSel) return;
    const p = savedPersonas.find((x) => x.id === savedSel);
    if (!p) return;
    setDraftFrame(p.frame);
    setDraftDescription(p.description);
    setDraftEmphasis(p.knowledge_emphasis.join(", "));
  }, [savedSel, savedPersonas]);

  const onSelectMockPersona = (p: Persona) => {
    setSel(p);
    setSavedSel(null);
    setDraftFrame(p.role);
    setDraftDescription(p.bias);
    setDraftEmphasis(p.beliefs.join(", "));
  };

  const onSave = () => {
    const knowledge_emphasis = draftEmphasis
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    createMutation.mutate({
      frame: draftFrame || sel.role,
      description: draftDescription || sel.bias,
      knowledge_emphasis,
    });
  };

  const onDelete = (id: string) => {
    if (savedSel === id) setSavedSel(null);
    deleteMutation.mutate(id);
  };

  const headerSub = apiOnline
    ? `// ${savedPersonas.length} saved · ${D.PERSONAS.length} cast`
    : `// ${D.PERSONAS.length} cast · auto-balance enabled`;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="05·PERSONAS"
        title="Persona Designer"
        breadcrumb={headerSub}
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            <MockBadge online={apiOnline} loading={status.loading} />
            <Btn ghost>+ ADD PERSONA</Btn>
            <Btn ghost>◫ TEMPLATE LIBRARY</Btn>
            <Btn ghost>◐ AUTO-BALANCE</Btn>
            <Btn primary onClick={onSave}>
              {createMutation.isPending ? "SAVING…" : "SAVE CAST →"}
            </Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden", padding: 16, gap: 12 }}>
          <div
            style={{
              border: "1px solid var(--line-2)",
              background: "var(--bg-2)",
              padding: 12,
            }}
          >
            <div
              className="row gap-2"
              style={{ alignItems: "center", marginBottom: 8 }}
            >
              <span
                className="tt-up"
                style={{ fontSize: 10, color: "var(--ink-2)" }}
              >
                SAVED PERSONAS
              </span>
              <span className="muted" style={{ fontSize: 9 }}>
                · {savedPersonas.length} on file
              </span>
              <div style={{ flex: 1 }} />
              {createMutation.isError && (
                <Chip tone="amber">save failed</Chip>
              )}
            </div>
            {!apiOnline ? (
              <div className="muted" style={{ fontSize: 10 }}>
                offline · using mock cast below
              </div>
            ) : savedPersonas.length === 0 ? (
              <div className="muted" style={{ fontSize: 10 }}>
                no saved personas yet — click SAVE CAST to create one
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 8,
                }}
              >
                {savedPersonas.map((p) => {
                  const isSel = savedSel === p.id;
                  return (
                    <div
                      key={p.id}
                      onClick={() => setSavedSel(p.id)}
                      style={{
                        border: `1px solid ${isSel ? "var(--amber)" : "var(--line-2)"}`,
                        background: isSel ? "var(--bg-3)" : "var(--bg-1)",
                        padding: "8px 10px",
                        cursor: "pointer",
                        display: "flex",
                        gap: 8,
                        alignItems: "flex-start",
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 11,
                            color: "var(--ink-0)",
                            fontWeight: 600,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {p.frame}
                        </div>
                        <div
                          style={{
                            fontSize: 10,
                            color: "var(--ink-2)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {p.description}
                        </div>
                        <div
                          className="tt-up"
                          style={{ fontSize: 9, color: "var(--ink-3)", marginTop: 2 }}
                        >
                          {p.knowledge_emphasis.length} emphasis
                        </div>
                      </div>
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(p.id);
                        }}
                        title="delete"
                        style={{
                          fontSize: 12,
                          color: "var(--ink-3)",
                          cursor: "pointer",
                          padding: "0 4px",
                        }}
                      >
                        ×
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

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
              const isSel = sel.id === p.id && !savedSel;
              return (
                <div
                  key={p.id}
                  onClick={() => onSelectMockPersona(p)}
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
              onClick={onSave}
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
                {apiOnline
                  ? "saves current designer state"
                  : "auto-balance suggests:"}
                {!apiOnline && (
                  <>
                    <br />
                    <span style={{ color: "var(--amber)" }}>
                      EU diplomat · KR security analyst
                    </span>
                  </>
                )}
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
              FRAME
            </div>
            <input
              value={draftFrame}
              onChange={(e) => setDraftFrame(e.target.value)}
              placeholder="e.g. skeptical regulator"
              style={{
                background: "var(--bg-0)",
                border: "1px solid var(--line-1)",
                color: "var(--ink-0)",
                padding: 8,
                fontFamily: "inherit",
                fontSize: 11,
                width: "100%",
                outline: "none",
              }}
            />
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", margin: "10px 0 6px" }}
            >
              DESCRIPTION
            </div>
            <textarea
              value={draftDescription}
              onChange={(e) => setDraftDescription(e.target.value)}
              placeholder="describe the viewpoint…"
              rows={3}
              style={{
                background: "var(--bg-0)",
                border: "1px solid var(--line-1)",
                color: "var(--ink-0)",
                padding: 8,
                fontFamily: "inherit",
                fontSize: 11,
                width: "100%",
                outline: "none",
                resize: "vertical",
              }}
            />
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", margin: "10px 0 6px" }}
            >
              KNOWLEDGE EMPHASIS · csv
            </div>
            <input
              value={draftEmphasis}
              onChange={(e) => setDraftEmphasis(e.target.value)}
              placeholder="trade policy, semiconductors"
              style={{
                background: "var(--bg-0)",
                border: "1px solid var(--line-1)",
                color: "var(--ink-0)",
                padding: 8,
                fontFamily: "inherit",
                fontSize: 11,
                width: "100%",
                outline: "none",
              }}
            />
            <Btn primary style={{ marginTop: 10 }} onClick={onSave}>
              {createMutation.isPending ? "SAVING…" : "SAVE PERSONA"}
            </Btn>
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
