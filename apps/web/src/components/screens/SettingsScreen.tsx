"use client";
import { Btn } from "@/components/ui/Btn";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { useThemeStore, type LightVariant, type ThemeMode } from "@/store/theme";

export function SettingsScreen() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const variant = useThemeStore((s) => s.lightVariant);
  const setVariant = useThemeStore((s) => s.setLightVariant);

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

          <Panel id="A" title="API Keys" style={{ marginTop: 16 }}>
            <div style={{ padding: 16 }}>
              {[
                "OPENAI_API_KEY",
                "GDELT_TOKEN",
                "REUTERS_KEY",
                "BRAVE_SEARCH",
                "X_BEARER",
                "WEIBO_KEY",
              ].map((k) => (
                <div
                  key={k}
                  className="row gap-2"
                  style={{
                    padding: "6px 0",
                    borderBottom: "1px solid var(--line-1)",
                    alignItems: "center",
                  }}
                >
                  <span
                    className="tt-up"
                    style={{ fontSize: 10, color: "var(--ink-1)", minWidth: 200 }}
                  >
                    {k}
                  </span>
                  <span className="tab muted" style={{ fontSize: 11 }}>
                    sk-···········x4f2
                  </span>
                  <div style={{ flex: 1 }} />
                  <Dot tone="green" />
                  <Btn ghost style={{ fontSize: 9 }}>
                    ROTATE
                  </Btn>
                </div>
              ))}
            </div>
          </Panel>

          <Panel id="B" title="Model Preferences" style={{ marginTop: 16 }}>
            <div style={{ padding: 16 }}>
              <KV k="Orchestrator" v="gpt-5.5" />
              <KV k="Personas (default)" v="gpt-5.4" />
              <KV k="Research" v="gpt-5.4-mini" />
              <KV k="Synthesizer" v="gpt-5.5" />
              <KV k="KG writer" v="gpt-5.4-mini" />
              <KV k="Cost ceiling / debate" v="$2.00" />
              <KV k="Hard limit / day" v="$50.00" />
            </div>
          </Panel>

          <Panel id="C" title="Persona Templates" style={{ marginTop: 16 }}>
            <div style={{ padding: 16, fontSize: 11, color: "var(--ink-1)" }}>
              42 templates · 18 official · 24 user · 7 starred
              <div style={{ marginTop: 8 }}>
                <Btn ghost>OPEN LIBRARY →</Btn>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
