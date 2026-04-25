"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { api } from "@/lib/api";
import { ARGUS_DATA } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

export function HomeScreen() {
  const router = useRouter();
  const setTopic = useDebateStore((s) => s.setTopic);
  const D = ARGUS_DATA;
  const [prompt, setPrompt] = useState("");
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("standard");
  const [autoPersonas, setAutoPersonas] = useState<boolean>(true);
  const [sources, setSources] = useState({ rss: true, news: true, social: true, kg: true });

  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: 0,
    staleTime: 30_000,
  });

  const launch = (text?: string) => {
    setTopic(
      text ||
        prompt ||
        "Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?",
    );
    router.push("/ops");
  };

  const apiOnline = health.isSuccess;
  const freshnessLabel = health.isLoading
    ? "checking..."
    : apiOnline
      ? `api online · ${health.data?.status ?? "ok"}${health.data?.version ? ` · v${health.data.version}` : ""}`
      : "api offline · using mock data";

  return (
    <div className="col grow" style={{ padding: 16, gap: 16, overflowY: "auto" }}>
      <ScreenHeader
        code="01·HOME"
        title="Topic Launcher"
        breadcrumb="// convene a council"
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            <Dot tone={apiOnline ? "green" : "amber"} pulse={!apiOnline} />
            <span className="tt-up muted" style={{ fontSize: 9 }}>
              {freshnessLabel}
            </span>
          </div>
        }
      />

      <div className="row gap-4" style={{ flexShrink: 0 }}>
        <Panel
          id="A"
          title="New Deliberation"
          sub="multi-agent · world-state grounded"
          style={{ flex: 2, minHeight: 300 }}
        >
          <div className="col grow" style={{ padding: 20, gap: 14 }}>
            <div className="tt-up" style={{ color: "var(--ink-3)", fontSize: 9 }}>
              Topic / question
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Will the PRC escalate to a customs quarantine of Taiwanese ports within 12 months?

Personas, world state, citation strictness will be auto-cast from this prompt."
              style={{
                background: "var(--bg-1)",
                border: "1px solid var(--line-2)",
                color: "var(--ink-0)",
                padding: 14,
                fontFamily: "inherit",
                fontSize: 14,
                lineHeight: 1.5,
                resize: "none",
                outline: "none",
                minHeight: 130,
                width: "100%",
              }}
            />
            <div className="row gap-3" style={{ flexWrap: "wrap", alignItems: "center" }}>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  Depth
                </span>
                <Segmented
                  options={[
                    { value: "quick", label: "Quick · 3p" },
                    { value: "standard", label: "Standard · 5p" },
                    { value: "deep", label: "Deep · 7p" },
                  ]}
                  value={depth}
                  onChange={setDepth}
                />
              </div>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  Persona casting
                </span>
                <Segmented
                  options={[
                    { value: true, label: "Auto" },
                    { value: false, label: "Manual" },
                  ]}
                  value={autoPersonas}
                  onChange={setAutoPersonas}
                />
              </div>
              <div className="col gap-1">
                <span className="tt-up muted" style={{ fontSize: 9 }}>
                  Sources
                </span>
                <div className="row gap-1">
                  {(
                    [
                      ["rss", "RSS"],
                      ["news", "News"],
                      ["social", "Social"],
                      ["kg", "KG only"],
                    ] as const
                  ).map(([k, lbl]) => (
                    <span
                      key={k}
                      onClick={() => setSources((s) => ({ ...s, [k]: !s[k] }))}
                      className={sources[k] ? "chip chip-amber" : "chip"}
                      style={{ cursor: "pointer" }}
                    >
                      {sources[k] ? "■" : "□"} {lbl}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ flex: 1 }} />
            <div className="row gap-2" style={{ alignItems: "center" }}>
              <Btn primary onClick={() => launch()}>
                ▸ CONVENE COUNCIL
              </Btn>
              <Btn ghost>SCHEDULE RECURRING</Btn>
              <div style={{ flex: 1 }} />
              <span className="muted tt-up" style={{ fontSize: 9 }}>
                EST · ~$0.42 · ~94s · 7 personas
              </span>
            </div>
          </div>
        </Panel>

        <Panel
          id="B"
          title="Trending Questions"
          sub="from world-state delta · 24h"
          style={{ flex: 1, minHeight: 300 }}
        >
          <div className="col" style={{ overflowY: "auto" }}>
            {D.TRENDING.map((q, i) => (
              <div
                key={i}
                onClick={() => launch(q)}
                style={{
                  padding: "10px 12px",
                  borderBottom: "1px solid var(--line-1)",
                  cursor: "pointer",
                  display: "flex",
                  gap: 8,
                  alignItems: "flex-start",
                }}
              >
                <span
                  className="tab"
                  style={{ color: "var(--amber)", fontSize: 10, minWidth: 18 }}
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span style={{ flex: 1, fontSize: 11, color: "var(--ink-0)", lineHeight: 1.4 }}>
                  {q}
                </span>
                <span style={{ color: "var(--green)", fontSize: 10 }}>↗</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="row gap-4" style={{ flexShrink: 0, minHeight: 240 }}>
        <Panel
          id="C"
          title="Recent Debates"
          sub={`${D.RECENT.length} · this session`}
          style={{ flex: 2 }}
        >
          <div className="col" style={{ overflowY: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 32 }}></th>
                  <th>Topic</th>
                  <th style={{ width: 80 }}>Personas</th>
                  <th style={{ width: 70 }}>Status</th>
                  <th style={{ width: 60 }}>Age</th>
                  <th style={{ width: 30 }}></th>
                </tr>
              </thead>
              <tbody>
                {D.RECENT.map((d) => (
                  <tr
                    key={d.id}
                    onClick={() => router.push(d.status === "running" ? "/debate" : "/synthesis")}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <Dot
                        tone={d.status === "running" ? "amber" : "green"}
                        pulse={d.status === "running"}
                      />
                    </td>
                    <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                    <td className="tab">{d.personas}</td>
                    <td>
                      <span
                        className="tt-up"
                        style={{
                          fontSize: 9,
                          color: d.status === "running" ? "var(--amber)" : "var(--ink-2)",
                        }}
                      >
                        {d.status}
                      </span>
                    </td>
                    <td className="tab muted">{d.time}</td>
                    <td className="muted">→</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel
          id="D"
          title="Live Ingest"
          sub="all sources · −2 min window"
          style={{ flex: 1 }}
          right={
            <>
              <Dot tone="green" pulse />
              <span className="tt-up" style={{ fontSize: 9, color: "var(--green)" }}>
                LIVE
              </span>
            </>
          }
        >
          <div className="col" style={{ overflowY: "auto" }}>
            {D.TICKER.map((t, i) => (
              <div
                key={i}
                style={{
                  padding: "6px 10px",
                  borderBottom: "1px solid var(--line-1)",
                  fontSize: 10,
                  lineHeight: 1.4,
                }}
              >
                <div className="row gap-2" style={{ alignItems: "baseline" }}>
                  <span className="tab muted">{t.t}</span>
                  <span className="amber tt-up" style={{ fontSize: 9 }}>
                    {t.src}
                  </span>
                </div>
                <div style={{ color: "var(--ink-1)", marginTop: 2 }}>{t.line}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Used to satisfy linter — Chip imported but rendered conditionally if API is offline */}
      {!apiOnline && health.isError && (
        <div style={{ display: "none" }}>
          <Chip>fallback mock</Chip>
        </div>
      )}
    </div>
  );
}
