"use client";
import { useQuery } from "@tanstack/react-query";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { MockBadge } from "@/components/ui/MockBadge";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";

// Env-var slots the server may have configured. Values are NEVER returned by
// the API — we only display the slot name and indicate "configured · server side".
const KEY_SLOTS = [
  "OPENAI_API_KEY",
  "QDRANT_API_KEY",
  "S3_ACCESS_KEY",
  "S3_SECRET_KEY",
  "HUGGINGFACE_TOKEN",
  "COHERE_API_KEY",
] as const;

const MODEL_ROLES: Array<{
  k: keyof import("@/lib/api").ConfigResponse["models"];
  label: string;
}> = [
  { k: "synthesis", label: "Synthesizer" },
  { k: "master", label: "Master / orchestrator" },
  { k: "persona", label: "Personas (default)" },
  { k: "research", label: "Research" },
  { k: "extractor", label: "Extractor" },
  { k: "verifier", label: "Verifier (cross-class)" },
  { k: "critic", label: "Critic" },
];

export function SettingsScreen() {
  const configQuery = useQuery({
    queryKey: ["config"],
    queryFn: api.config,
    retry: 0,
    staleTime: 60_000,
  });

  const status = apiStatus(configQuery);
  const cfg = configQuery.data;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="·SETTINGS"
        title="Settings"
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            <MockBadge online={status.online} loading={status.loading} />
          </div>
        }
      />
      <div className="grow" style={{ overflowY: "auto", padding: 24 }}>
        <div style={{ maxWidth: 720 }}>
          <Panel id="A" title="API Keys">
            <div style={{ padding: 16 }}>
              <div
                className="muted"
                style={{ fontSize: 10, marginBottom: 8 }}
              >
                Values live in server env. The UI never reads or displays
                secrets — slots below show only configuration intent.
              </div>
              {KEY_SLOTS.map((k) => (
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
                    configured · server side
                  </span>
                  <div style={{ flex: 1 }} />
                  <Dot tone="green" />
                  <Btn ghost style={{ fontSize: 9 }} onClick={() => { /* no-op for now */ }}>
                    ROTATE
                  </Btn>
                </div>
              ))}
            </div>
          </Panel>

          <Panel id="B" title="Model Preferences" style={{ marginTop: 16 }}>
            <div style={{ padding: 16 }}>
              {configQuery.isLoading && (
                <div className="muted" style={{ fontSize: 11 }}>
                  loading config…
                </div>
              )}
              {configQuery.isError && (
                <div className="muted" style={{ fontSize: 11 }}>
                  failed to read /config — showing nothing.
                </div>
              )}
              {cfg && (
                <>
                  {MODEL_ROLES.map(({ k, label }) => (
                    <KV key={k} k={label} v={cfg.models[k]} />
                  ))}
                  <KV k="Embedding model" v={cfg.embedding_model} />
                  <KV k="Reranker model" v={cfg.reranker_model} />
                </>
              )}
            </div>
          </Panel>

          <Panel id="C" title="Persona Templates" style={{ marginTop: 16 }}>
            <div style={{ padding: 16, fontSize: 11, color: "var(--ink-1)" }}>
              <div className="row gap-2" style={{ alignItems: "center", marginBottom: 8 }}>
                <span>42 templates · 18 official · 24 user · 7 starred</span>
                <Chip tone="amber">demo</Chip>
              </div>
              <div style={{ marginTop: 8 }}>
                <Btn ghost>OPEN LIBRARY →</Btn>
              </div>
            </div>
          </Panel>

          <Panel id="D" title="Vertical" style={{ marginTop: 16 }}>
            <div style={{ padding: 16, fontSize: 11, color: "var(--ink-1)" }}>
              <div className="row gap-2" style={{ alignItems: "center", marginBottom: 6 }}>
                <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-2)" }}>
                  Active vertical
                </span>
                <div style={{ flex: 1 }} />
                <Chip tone="amber">{cfg?.vertical ?? "—"}</Chip>
              </div>
              <KV k="Qdrant collection" v={cfg?.qdrant.collection ?? "—"} />
              <KV k="Trust tiers config" v="config/trust_tiers.yaml" />
            </div>
          </Panel>

          <Panel id="E" title="Ingest schedule" style={{ marginTop: 16 }}>
            <div style={{ padding: 16, fontSize: 11, color: "var(--ink-1)" }}>
              <div className="row gap-2" style={{ alignItems: "center", marginBottom: 6 }}>
                <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-2)" }}>
                  Status
                </span>
                <div style={{ flex: 1 }} />
                {cfg ? (
                  <Chip tone={cfg.ingest.enabled ? "green" : "default"}>
                    {cfg.ingest.enabled ? "enabled" : "disabled"}
                  </Chip>
                ) : (
                  <span className="muted">—</span>
                )}
              </div>
              <KV
                k="Interval"
                v={cfg ? `${cfg.ingest.interval_seconds}s` : "—"}
              />
              <KV
                k="Max items / feed"
                v={cfg ? String(cfg.ingest.max_items_per_feed) : "—"}
              />
              <KV k="Feeds path" v={cfg?.ingest.feeds_path ?? "—"} />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
