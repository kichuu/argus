"use client";
import { Btn } from "@/components/ui/Btn";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { Sparkline } from "@/components/ui/Sparkline";

const KPIS = [
  { lbl: "DEBATES 24H", v: "47", spark: [3, 4, 2, 5, 4, 6, 5, 7, 8, 6, 5, 4], c: "var(--amber)" },
  { lbl: "TOK 24H", v: "1.42M", spark: [80, 120, 90, 140, 180, 160, 220, 190, 250, 210, 240, 280], c: "var(--green)" },
  { lbl: "COST 24H", v: "$31.06", spark: [2, 3, 2, 4, 5, 4, 6, 5, 7, 6, 7, 8], c: "var(--ink-0)" },
  { lbl: "ERR RATE", v: "0.4%", spark: [1, 0.8, 0.6, 0.4, 0.5, 0.3, 0.4, 0.4, 0.4, 0.5, 0.4, 0.4], c: "var(--red)" },
];

const TRACES: [string, string, string, string, string, string][] = [
  ["d-2026-04-25-01·ORCH", "gpt-4.1", "8.2k", "$0.18", "12.4s", "ok"],
  ["d-2026-04-25-01·LAI", "gpt-4.1", "2.1k", "$0.04", "3.1s", "ok"],
  ["d-2026-04-25-01·XI", "gpt-4.1", "1.8k", "$0.03", "2.8s", "ok"],
  ["d-2026-04-25-01·INDO", "gpt-4.1", "3.4k", "$0.07", "4.2s", "ok"],
  ["d-2026-04-25-01·TSMC", "gpt-4.1", "1.6k", "$0.03", "2.5s", "ok"],
  ["d-2026-04-25-01·KG", "gpt-4o-mini", "12k", "$0.04", "8.1s", "ok"],
  ["d-2026-04-24-04·SYNTH", "gpt-4.1", "9.4k", "$0.21", "14.2s", "ok"],
  ["src.planet·INGEST", "—", "—", "—", "—", "fail"],
  ["d-2026-04-24-02·ORCH", "gpt-4.1", "6.8k", "$0.15", "10.1s", "ok"],
];

export function ObsScreen() {
  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="12·OBS"
        title="Observability"
        breadcrumb="// phoenix · temporal · evals"
        right={
          <div className="row gap-2">
            <Segmented size="sm" options={["1h", "24h", "7d", "30d"]} value="24h" onChange={() => {}} />
            <Btn ghost>↗ PHOENIX</Btn>
          </div>
        }
      />
      <div className="grow" style={{ overflowY: "auto", padding: 16 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
            marginBottom: 16,
          }}
        >
          {KPIS.map((s) => (
            <Panel key={s.lbl}>
              <div style={{ padding: 14 }}>
                <div className="tt-up muted" style={{ fontSize: 9 }}>
                  {s.lbl}
                </div>
                <div className="tab" style={{ fontSize: 24, color: s.c, fontWeight: 600 }}>
                  {s.v}
                </div>
                <Sparkline data={s.spark} width="100%" height={28} color={s.c} />
              </div>
            </Panel>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Panel id="T" title="Traces" sub="last 9 · phoenix">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Trace</th>
                  <th>Model</th>
                  <th>Tok</th>
                  <th>$</th>
                  <th>Lat</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {TRACES.map((r, i) => (
                  <tr key={i}>
                    <td className="tab muted">{r[0]}</td>
                    <td>{r[1]}</td>
                    <td className="tab">{r[2]}</td>
                    <td className="tab">{r[3]}</td>
                    <td className="tab">{r[4]}</td>
                    <td>
                      <span
                        style={{ color: r[5] === "ok" ? "var(--green)" : "var(--red)" }}
                        className="tt-up"
                      >
                        {r[5]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <Panel id="W" title="Workflows" sub="temporal · running">
            <div style={{ padding: 14, fontFamily: "JetBrains Mono", fontSize: 10, lineHeight: 1.7 }}>
              <div>
                <span className="green">▸</span> deliberation_v3 · d-2026-04-25-01 · turn 13/14 · running 1m 34s
              </div>
              <div>
                <span className="amber">▸</span> ingest_loop · running 14h 22m · 14k events
              </div>
              <div>
                <span className="amber">▸</span> kg_writer · running 14h 22m · queue 3
              </div>
              <div>
                <span className="green">✓</span> deliberation_v3 · d-2026-04-24-04 · 1m 41s
              </div>
              <div>
                <span className="green">✓</span> deliberation_v3 · d-2026-04-24-02 · 2m 08s
              </div>
              <div>
                <span className="red">✗</span> ingest_planet · 3 retries exceeded · 8h 42m ago
              </div>
              <div>
                <span className="green">✓</span> eval_consensus_quality · 47 debates · 4m 12s
              </div>
            </div>
          </Panel>

          <Panel id="P" title="Prompt Diffs" sub="auto-tuning history">
            <div style={{ padding: 14, fontFamily: "JetBrains Mono", fontSize: 10, lineHeight: 1.7 }}>
              <div>
                <span className="muted">2026-04-24 18:02</span> · <span className="green">+0.04</span>{" "}
                consensus quality · orchestrator.cast_personas · v.42
              </div>
              <div>
                <span className="muted">2026-04-23 09:14</span> · <span className="green">+0.02</span>{" "}
                citation rate · persona.synthesize · v.31
              </div>
              <div>
                <span className="muted">2026-04-22 22:48</span> · <span className="red">−0.01</span> rolled
                back · persona.challenge · v.18
              </div>
              <div>
                <span className="muted">2026-04-21 11:30</span> · <span className="green">+0.06</span>{" "}
                minority capture · synthesizer · v.27
              </div>
            </div>
          </Panel>

          <Panel id="E" title="Evals" sub="last run · 47 debates">
            <div style={{ padding: 14 }}>
              <KV k="Consensus quality" v="0.78" vColor="var(--green)" />
              <KV k="Citation coverage" v="0.91" vColor="var(--green)" />
              <KV k="Persona drift" v="0.06" vColor="var(--green)" />
              <KV k="Synthesizer faithfulness" v="0.84" vColor="var(--green)" />
              <KV k="Hallucination rate" v="0.011" vColor="var(--green)" />
              <KV k="Adversarial hold-out" v="0.71" vColor="var(--amber)" />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
