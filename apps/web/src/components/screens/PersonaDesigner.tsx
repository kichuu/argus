"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockBadge } from "@/components/ui/MockBadge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type PersonaSummary } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";

const MODEL_OPTIONS = [
  "openai:gpt-4o",
  "openai:gpt-4o-mini",
  "openai:gpt-4.1",
  "openai:o4-mini",
] as const;

const _PALETTE = [
  "var(--p-1)",
  "var(--p-2)",
  "var(--p-3)",
  "var(--p-4)",
  "var(--p-5)",
  "var(--p-6)",
  "var(--p-7)",
];

function colorForFrame(frame: string): string {
  if (!frame) return "var(--ink-2)";
  let h = 0;
  for (let i = 0; i < frame.length; i++) h = (h + frame.charCodeAt(i)) | 0;
  return _PALETTE[Math.abs(h) % _PALETTE.length];
}

const EMPTY_DRAFT = {
  frame: "",
  description: "",
  emphasis: "",
  bias: "",
  model: MODEL_OPTIONS[0] as string,
  temperature: 0.7,
  redlines: "",
};

export function PersonaDesigner() {
  const qc = useQueryClient();
  const [savedSel, setSavedSel] = useState<string | null>(null);
  const [draftFrame, setDraftFrame] = useState<string>(EMPTY_DRAFT.frame);
  const [draftDescription, setDraftDescription] = useState<string>(EMPTY_DRAFT.description);
  const [draftEmphasis, setDraftEmphasis] = useState<string>(EMPTY_DRAFT.emphasis);
  const [draftTemperature, setDraftTemperature] = useState<number>(EMPTY_DRAFT.temperature);
  const [draftRedlines, setDraftRedlines] = useState<string>(EMPTY_DRAFT.redlines);
  const [draftBias, setDraftBias] = useState<string>(EMPTY_DRAFT.bias);
  const [draftModel, setDraftModel] = useState<string>(EMPTY_DRAFT.model);

  const personasQuery = useQuery({
    queryKey: ["personas"],
    queryFn: api.personas,
    retry: 0,
    staleTime: 30_000,
  });

  const status = apiStatus(personasQuery);
  const apiOnline = status.online;

  const savedPersonas: PersonaSummary[] = useMemo(
    () => (personasQuery.data ?? []) as PersonaSummary[],
    [personasQuery.data],
  );

  const createMutation = useMutation({
    mutationFn: (body: {
      frame: string;
      description: string;
      knowledge_emphasis: string[];
      temperature: number;
      redlines: string[];
      bias: string | null;
      model_assignment: string | null;
    }) => api.createPersona(body),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["personas"] });
      if (created?.id) setSavedSel(created.id);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: {
      id: string;
      patch: {
        frame: string;
        description: string;
        knowledge_emphasis: string[];
        temperature: number;
        redlines: string[];
        bias: string | null;
        model_assignment: string | null;
      };
    }) => api.updatePersona(vars.id, vars.patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePersona(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
      setSavedSel(null);
    },
  });

  // Load a saved persona into the designer.
  useEffect(() => {
    if (!savedSel) return;
    const p = savedPersonas.find((x) => x.id === savedSel);
    if (!p) return;
    setDraftFrame(p.frame);
    setDraftDescription(p.description);
    setDraftEmphasis(p.knowledge_emphasis.join(", "));
    setDraftTemperature(p.temperature ?? 0.7);
    setDraftRedlines((p.redlines ?? []).join("\n"));
    setDraftBias(p.bias ?? "");
    setDraftModel(p.model_assignment ?? MODEL_OPTIONS[0]);
  }, [savedSel, savedPersonas]);

  const resetDraft = () => {
    setSavedSel(null);
    setDraftFrame(EMPTY_DRAFT.frame);
    setDraftDescription(EMPTY_DRAFT.description);
    setDraftEmphasis(EMPTY_DRAFT.emphasis);
    setDraftTemperature(EMPTY_DRAFT.temperature);
    setDraftRedlines(EMPTY_DRAFT.redlines);
    setDraftBias(EMPTY_DRAFT.bias);
    setDraftModel(EMPTY_DRAFT.model);
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const draftValid = draftFrame.trim().length > 0 && draftDescription.trim().length > 0;
  const saveDisabled = !apiOnline || isSaving || !draftValid;

  const onSave = () => {
    if (!apiOnline || !draftValid) return;
    const knowledge_emphasis = draftEmphasis
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const redlines = draftRedlines
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    const payload = {
      frame: draftFrame.trim(),
      description: draftDescription.trim(),
      knowledge_emphasis,
      temperature: draftTemperature,
      redlines,
      bias: draftBias.trim() ? draftBias.trim() : null,
      model_assignment: draftModel || null,
    };
    if (savedSel) {
      updateMutation.mutate({ id: savedSel, patch: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const onDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const headerSub = `// ${savedPersonas.length} saved`;
  const draftColor = colorForFrame(draftFrame);
  const draftInitial = draftFrame.trim().charAt(0).toUpperCase() || "·";
  const redlineCount = draftRedlines
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean).length;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="05·PERSONAS"
        title="Persona Designer"
        breadcrumb={headerSub}
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            <MockBadge online={apiOnline} loading={status.loading} />
            {!apiOnline && <Chip tone="amber">offline · save disabled</Chip>}
            <Btn ghost onClick={resetDraft}>
              + NEW
            </Btn>
            <Btn primary onClick={onSave} disabled={saveDisabled}>
              {isSaving ? "SAVING…" : savedSel ? "UPDATE PERSONA →" : "SAVE PERSONA →"}
            </Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        {/* Left: saved personas grid */}
        <div className="grow col" style={{ overflow: "hidden", padding: 16, gap: 12 }}>
          <div
            className="row gap-2"
            style={{ alignItems: "center" }}
          >
            <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-2)" }}>
              SAVED PERSONAS
            </span>
            <span className="muted" style={{ fontSize: 9 }}>
              · {savedPersonas.length} on file
            </span>
            <div style={{ flex: 1 }} />
            {(createMutation.isError || updateMutation.isError) && (
              <Chip tone="amber">save failed</Chip>
            )}
          </div>

          {personasQuery.isLoading ? (
            <div className="muted" style={{ fontSize: 11 }}>loading personas…</div>
          ) : savedPersonas.length === 0 ? (
            <EmptyState
              title="No saved personas yet"
              hint="Frames like 'skeptical empiricist' or 'regulator viewpoint' get cast into debates by the master agent. Fill the form on the right and click SAVE."
            />
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                gap: 12,
                overflowY: "auto",
                paddingRight: 4,
              }}
            >
              {savedPersonas.map((p) => {
                const isSel = savedSel === p.id;
                const color = p.color || colorForFrame(p.frame);
                const initial = p.frame.charAt(0).toUpperCase() || "·";
                return (
                  <div
                    key={p.id}
                    onClick={() => setSavedSel(p.id)}
                    style={{
                      padding: 14,
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: 10,
                      border: `${isSel ? 2 : 1}px solid ${isSel ? color : "var(--line-2)"}`,
                      background: isSel ? "var(--bg-3)" : "var(--bg-2)",
                    }}
                  >
                    <div className="row gap-3" style={{ alignItems: "flex-start" }}>
                      <div
                        style={{
                          width: 42,
                          height: 42,
                          background: color,
                          color: "var(--bg-0)",
                          fontWeight: 700,
                          fontSize: 18,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        {initial}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600 }}>
                          {p.frame}
                        </div>
                        <div className="tt-up" style={{ fontSize: 9, color, marginTop: 2 }}>
                          {p.model_assignment ?? "model unset"}
                        </div>
                      </div>
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(p.id);
                        }}
                        title="delete"
                        style={{
                          fontSize: 14,
                          color: "var(--ink-3)",
                          cursor: "pointer",
                          padding: "0 4px",
                        }}
                      >
                        ×
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--ink-1)",
                        lineHeight: 1.4,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        display: "-webkit-box",
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: "vertical",
                      }}
                    >
                      {p.description}
                    </div>
                    <div className="row gap-2" style={{ flexWrap: "wrap" }}>
                      {p.knowledge_emphasis.slice(0, 3).map((k, i) => (
                        <Chip key={i}>{k}</Chip>
                      ))}
                      {p.knowledge_emphasis.length > 3 && (
                        <span className="muted" style={{ fontSize: 9 }}>
                          +{p.knowledge_emphasis.length - 3}
                        </span>
                      )}
                    </div>
                    <div className="row gap-2" style={{ alignItems: "center" }}>
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                        TEMP
                      </span>
                      <span className="tab" style={{ fontSize: 10, color: "var(--ink-1)" }}>
                        {(p.temperature ?? 0.7).toFixed(2)}
                      </span>
                      <div style={{ flex: 1 }} />
                      <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                        ⛔ {(p.redlines ?? []).length}
                      </span>
                    </div>
                  </div>
                );
              })}
              <div
                onClick={resetDraft}
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
                <div className="tt-up">NEW PERSONA</div>
                <div style={{ fontSize: 10, marginTop: 4, textAlign: "center" }}>
                  resets the editor to a blank frame
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: editor */}
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
              <div
                style={{
                  width: 48,
                  height: 48,
                  background: draftColor,
                  color: "var(--bg-0)",
                  fontWeight: 700,
                  fontSize: 22,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {draftInitial}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 16, color: "var(--ink-0)", fontWeight: 600 }}>
                  {draftFrame.trim() || "untitled frame"}
                </div>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: draftColor, marginTop: 4 }}
                >
                  {savedSel ? "editing" : "new"} · {draftModel}
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
              placeholder="e.g. skeptical empiricist"
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
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", margin: "10px 0 6px" }}
            >
              BIAS
            </div>
            <input
              value={draftBias}
              onChange={(e) => setDraftBias(e.target.value)}
              placeholder="short bias label, e.g. cautious-regulator"
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
              MODEL ASSIGNMENT
            </div>
            <select
              value={draftModel}
              onChange={(e) => setDraftModel(e.target.value)}
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
            >
              {!MODEL_OPTIONS.includes(draftModel as (typeof MODEL_OPTIONS)[number]) && (
                <option value={draftModel}>{draftModel}</option>
              )}
              {MODEL_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--red)", marginBottom: 8 }}
            >
              RED LINES · constitution
            </div>
            <textarea
              value={draftRedlines}
              onChange={(e) => setDraftRedlines(e.target.value)}
              placeholder="one redline per line — claims this persona refuses to make"
              rows={4}
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
            <div className="muted" style={{ fontSize: 9, marginTop: 4 }}>
              {redlineCount} redline(s) · one per line
            </div>
          </div>

          <div style={{ padding: 14 }}>
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 8 }}
            >
              TUNING
            </div>
            <div className="row gap-2" style={{ alignItems: "center", padding: "5px 0" }}>
              <span
                className="tt-up"
                style={{ fontSize: 9, color: "var(--ink-2)", minWidth: 110 }}
              >
                Temperature
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={draftTemperature}
                onChange={(e) => setDraftTemperature(Number(e.target.value))}
                style={{ flex: 1, accentColor: draftColor }}
              />
              <span
                className="tab"
                style={{
                  fontSize: 10,
                  color: "var(--ink-1)",
                  minWidth: 32,
                  textAlign: "right",
                }}
              >
                {draftTemperature.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
