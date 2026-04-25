"use client";
import { useQuery } from "@tanstack/react-query";
import { Chip } from "@/components/ui/Chip";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { api, type SettingsResponse } from "@/lib/api";
import { useThemeStore, type LightVariant, type ThemeMode } from "@/store/theme";

function familyTone(family: string): "green" | "amber" | "default" {
  if (family === "gpt") return "green";
  if (family === "reasoning") return "amber";
  return "default";
}

export function SettingsScreen() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const variant = useThemeStore((s) => s.lightVariant);
  const setVariant = useThemeStore((s) => s.setLightVariant);

  const settingsQ = useQuery<SettingsResponse>({
    queryKey: ["settings"],
    queryFn: () => api.settings(),
    staleTime: 60_000,
    retry: 0,
  });

  const data = settingsQ.data;
  const personaEntries = data
    ? Object.entries(data.persona_library_count).sort(([a], [b]) => a.localeCompare(b))
    : [];

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="·SETTINGS" title="Settings" />
      <div className="grow" style={{ overflowY: "auto", padding: 24 }}>
        <div style={{ maxWidth: 720 }}>
          <Panel id="THEME" title="Theme">
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="row gap-3" style={{ alignItems: "center" }}>
                <span
                  className="tt-up"
                  style={{ fontSize: 10, color: "var(--ink-2)", minWidth: 110 }}
                >
                  Mode
                </span>
                <Segmented<ThemeMode>
                  options={[
                    { value: "dark", label: "Dark" },
                    { value: "light", label: "Light" },
                  ]}
                  value={theme}
                  onChange={setTheme}
                />
              </div>
              {theme === "light" && (
                <div className="row gap-3" style={{ alignItems: "center" }}>
                  <span
                    className="tt-up"
                    style={{ fontSize: 10, color: "var(--ink-2)", minWidth: 110 }}
                  >
                    Light palette
                  </span>
                  <Segmented<LightVariant>
                    options={[
                      { value: "paper", label: "Paper" },
                      { value: "cool", label: "Cool" },
                      { value: "ledger", label: "Ledger" },
                    ]}
                    value={variant}
                    onChange={setVariant}
                  />
                </div>
              )}
            </div>
          </Panel>

          {settingsQ.isError && (
            <Panel id="ERR" title="Backend" style={{ marginTop: 16 }}>
              <div style={{ padding: 16, fontSize: 11, color: "var(--red)" }}>
                settings unavailable — backend not reachable
              </div>
            </Panel>
          )}

          {settingsQ.isLoading && !data && (
            <Panel id="LOAD" title="Configuration" style={{ marginTop: 16 }}>
              <div style={{ padding: 16, fontSize: 11, color: "var(--ink-3)" }}>
                loading settings...
              </div>
            </Panel>
          )}

          {data && (
            <>
              <Panel id="MODELS" title="Models" style={{ marginTop: 16 }}>
                <div style={{ padding: 16 }}>
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th style={{ width: 140 }}>Role</th>
                        <th>Model</th>
                        <th style={{ width: 110 }}>Family</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.models.map((m) => (
                        <tr key={m.role}>
                          <td>
                            <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-2)" }}>
                              {m.role}
                            </span>
                          </td>
                          <td className="tab" style={{ color: "var(--ink-0)" }}>
                            {m.model}
                          </td>
                          <td>
                            <Chip tone={familyTone(m.family)}>{m.family}</Chip>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel id="VERTICAL" title="Vertical" style={{ marginTop: 16 }}>
                <div style={{ padding: 16 }}>
                  <KV k="Default vertical" v={data.vertical} />
                </div>
              </Panel>

              <Panel id="EMBEDDING" title="Embedding" style={{ marginTop: 16 }}>
                <div style={{ padding: 16 }}>
                  <KV k="Provider" v={data.embedding_provider} />
                  <KV
                    k="Model"
                    v={
                      data.embedding_provider === "openai"
                        ? data.openai_embedding_model
                        : data.embedding_model
                    }
                  />
                  <KV k="Dimensions" v={String(data.openai_embedding_dimensions)} />
                  <KV k="Reranker" v={data.reranker_model} />
                </div>
              </Panel>

              <Panel id="TRUST" title="Trust tiers" style={{ marginTop: 16 }}>
                <div style={{ padding: 16 }}>
                  <KV k="Tiers + domain overrides" v={String(data.trust_tier_count)} />
                </div>
              </Panel>

              <Panel id="PERSONAS" title="Persona library" style={{ marginTop: 16 }}>
                <div style={{ padding: 16 }}>
                  {personaEntries.length === 0 ? (
                    <div style={{ fontSize: 11, color: "var(--ink-3)" }}>
                      ── no persona templates loaded ──
                    </div>
                  ) : (
                    <table className="tbl">
                      <thead>
                        <tr>
                          <th>Vertical</th>
                          <th style={{ width: 100 }}>Frames</th>
                        </tr>
                      </thead>
                      <tbody>
                        {personaEntries.map(([vertical, count]) => (
                          <tr key={vertical}>
                            <td>
                              <span
                                className="tt-up"
                                style={{ fontSize: 10, color: "var(--ink-2)" }}
                              >
                                {vertical}
                              </span>
                            </td>
                            <td className="tab" style={{ color: "var(--ink-0)" }}>
                              {count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </Panel>

              <Panel id="INFRA" title="Infrastructure" style={{ marginTop: 16 }}>
                <div style={{ padding: 16 }}>
                  <KV k="App env" v={data.app_env} />
                  <KV k="Log level" v={data.log_level} />
                  <KV k="Qdrant collection" v={data.qdrant_collection} />
                  <KV k="Temporal host" v={data.temporal.host} />
                  <KV k="Temporal namespace" v={data.temporal.namespace} />
                  <KV k="Temporal task queue" v={data.temporal.task_queue} />
                  <KV k="Raw store backend" v={data.raw_store_backend} />
                </div>
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
