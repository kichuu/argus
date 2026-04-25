"use client";
import { Btn } from "@/components/ui/Btn";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";

const KEYS = [
  "OPENAI_API_KEY",
  "GDELT_BASE",
  "QDRANT_URL",
  "TEMPORAL_HOST",
  "COHERE_API_KEY",
  "HUGGINGFACE_TOKEN",
];

export function SettingsScreen() {
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader code="·SETTINGS" title="Settings" />
      <div className="grow" style={{ overflowY: "auto", padding: 24 }}>
        <div style={{ maxWidth: 720 }}>
          <Panel id="A" title="API Keys">
            <div style={{ padding: 16 }}>
              {KEYS.map((k) => (
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
              <KV k="Synthesizer" v="gpt-5.5 (verify)" />
              <KV k="Master / orchestrator" v="gpt-5.5 (verify)" />
              <KV k="Personas (default)" v="gpt-5.4 (verify)" />
              <KV k="Research" v="gpt-5.5 (verify)" />
              <KV k="Verifier (cross-class)" v="o4-mini" />
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
          <Panel id="D" title="Vertical" style={{ marginTop: 16 }}>
            <div style={{ padding: 16, fontSize: 11, color: "var(--ink-1)" }}>
              <KV k="Active vertical" v="geopolitics" vColor="var(--amber)" />
              <KV k="In-scope topics" v="8 (see config/vertical.yaml)" />
              <KV k="Trust tiers config" v="config/trust_tiers.yaml" />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
