"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { ARGUS_DATA, type GeoEvent } from "@/mock/data";
import { useDebateStore } from "@/store/debate";

const W = 1000;
const H = 500;

const project = (lat: number, lon: number) => ({
  x: ((lon + 180) / 360) * W,
  y: ((90 - lat) / 180) * H,
});

export function WorldView() {
  const router = useRouter();
  const setTopic = useDebateStore((s) => s.setTopic);
  const D = ARGUS_DATA;
  const [layer, setLayer] = useState<"events" | "heat" | "flow">("events");
  const [time, setTime] = useState<"24h" | "7d" | "30d">("24h");
  const [topic, setTopic2] = useState<string>("all");
  const [hover, setHover] = useState<GeoEvent | null>(null);
  const [sel, setSel] = useState<GeoEvent | null>(D.EVENTS[0]);

  const filtered = topic === "all" ? D.EVENTS : D.EVENTS.filter((e) => e.topic === topic);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="02·WORLD"
        title="WorldView"
        breadcrumb="// 24h · all topics · 24 events"
        right={
          <div className="row gap-2">
            <Segmented
              options={[
                { value: "events", label: "Events" },
                { value: "heat", label: "Heat" },
                { value: "flow", label: "Flow" },
              ]}
              value={layer}
              onChange={setLayer}
            />
            <Segmented
              options={["24h", "7d", "30d"] as const}
              value={time}
              onChange={setTime}
            />
            <Btn ghost>◐ 3D / 2D</Btn>
            <Btn ghost>↗ SHARE</Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          className="grow col grid-bg"
          style={{ position: "relative", overflow: "hidden", background: "var(--bg-1)" }}
        >
          <div
            style={{
              position: "absolute",
              top: 12,
              left: 12,
              zIndex: 10,
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
            }}
          >
            {["all", "TW Strait", "Markets", "Defense", "Diplomatic", "Supply Chain", "SCS"].map(
              (t) => (
                <span
                  key={t}
                  onClick={() => setTopic2(t)}
                  className={topic === t ? "chip chip-amber" : "chip"}
                  style={{ cursor: "pointer" }}
                >
                  {t}
                </span>
              ),
            )}
          </div>

          <svg
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: "100%", height: "100%", display: "block" }}
            preserveAspectRatio="xMidYMid meet"
          >
            {Array.from({ length: 13 }).map((_, i) => (
              <line
                key={"g" + i}
                x1={i * (W / 12)}
                y1={0}
                x2={i * (W / 12)}
                y2={H}
                stroke="var(--line-1)"
                strokeWidth="0.5"
              />
            ))}
            {Array.from({ length: 7 }).map((_, i) => (
              <line
                key={"h" + i}
                x1={0}
                y1={i * (H / 6)}
                x2={W}
                y2={i * (H / 6)}
                stroke="var(--line-1)"
                strokeWidth="0.5"
              />
            ))}
            <line x1={0} y1={H / 2} x2={W} y2={H / 2} stroke="var(--line-2)" strokeWidth="1" strokeDasharray="4 4" />

            <g fill="var(--bg-3)" stroke="var(--line-2)" strokeWidth="0.6">
              <path d="M 100,140 L 180,110 L 240,130 L 280,180 L 250,240 L 220,260 L 180,280 L 140,260 L 110,200 Z" />
              <path d="M 240,300 L 280,290 L 300,340 L 295,400 L 270,440 L 250,420 L 240,360 Z" />
              <path d="M 470,140 L 520,130 L 540,160 L 530,190 L 490,200 L 470,180 Z" />
              <path d="M 480,220 L 540,210 L 570,260 L 580,330 L 540,380 L 510,380 L 490,320 L 480,260 Z" />
              <path d="M 540,130 L 720,120 L 800,160 L 820,200 L 790,240 L 720,260 L 660,250 L 600,230 L 560,200 L 540,170 Z" />
              <path d="M 720,260 L 800,270 L 820,300 L 780,310 L 740,300 Z" />
              <path d="M 790,330 L 870,330 L 880,370 L 830,390 L 790,370 Z" />
              <path d="M 380,80 L 430,70 L 440,110 L 410,130 L 380,110 Z" />
              <path d="M 0,470 L 1000,470 L 1000,500 L 0,500 Z" />
              <path d="M 800,200 L 820,195 L 825,220 L 810,225 Z" />
              <path d="M 460,150 L 470,148 L 472,168 L 462,170 Z" />
            </g>

            {layer === "heat" &&
              filtered.map((e) => {
                const p = project(e.lat, e.lon);
                return (
                  <circle
                    key={"hh" + e.id}
                    cx={p.x}
                    cy={p.y}
                    r={e.severity * 60}
                    fill="var(--amber)"
                    opacity={e.severity * 0.18}
                  />
                );
              })}

            {layer === "flow" &&
              (() => {
                const tw = D.EVENTS.find((e) => e.id === "e1");
                if (!tw) return null;
                const tp = project(tw.lat, tw.lon);
                return D.EVENTS.filter((e) => e.id !== "e1" && e.severity > 0.5).map((e) => {
                  const ep = project(e.lat, e.lon);
                  const mx = (tp.x + ep.x) / 2;
                  const my = Math.min(tp.y, ep.y) - 60;
                  return (
                    <path
                      key={"arc" + e.id}
                      d={`M ${tp.x} ${tp.y} Q ${mx} ${my} ${ep.x} ${ep.y}`}
                      stroke="var(--amber)"
                      strokeWidth="1"
                      fill="none"
                      strokeDasharray="3 3"
                      opacity="0.5"
                    />
                  );
                });
              })()}

            {filtered.map((e) => {
              const p = project(e.lat, e.lon);
              const isSel = sel?.id === e.id;
              const isHover = hover?.id === e.id;
              const r = 3 + e.severity * 6;
              const color =
                e.severity > 0.75
                  ? "var(--red)"
                  : e.severity > 0.5
                    ? "var(--amber)"
                    : "var(--ink-1)";
              return (
                <g
                  key={e.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => setSel(e)}
                  onMouseEnter={() => setHover(e)}
                  onMouseLeave={() => setHover(null)}
                >
                  {(isSel || isHover) && (
                    <circle cx={p.x} cy={p.y} r={r * 2.5} fill={color} opacity="0.18" />
                  )}
                  <circle cx={p.x} cy={p.y} r={r} fill={color} opacity="0.9" />
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={r + 2}
                    fill="none"
                    stroke={color}
                    strokeWidth="0.6"
                    opacity="0.6"
                  >
                    <animate attributeName="r" from={r} to={r + 8} dur="2s" repeatCount="indefinite" />
                    <animate
                      attributeName="opacity"
                      from="0.6"
                      to="0"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                  </circle>
                  {(isSel || isHover) && (
                    <g>
                      <line
                        x1={p.x}
                        y1={p.y}
                        x2={p.x + 14}
                        y2={p.y - 14}
                        stroke={color}
                        strokeWidth="0.8"
                      />
                      <text
                        x={p.x + 16}
                        y={p.y - 14}
                        fill="var(--ink-0)"
                        fontSize="9"
                        fontFamily="JetBrains Mono"
                      >
                        {e.label}
                      </text>
                      <text
                        x={p.x + 16}
                        y={p.y - 4}
                        fill="var(--ink-3)"
                        fontSize="8"
                        fontFamily="JetBrains Mono"
                      >
                        {e.country} · {e.topic}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            <text x={10} y={18} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">
              EQUIRECTANGULAR · WGS84 · ZOOM 1.0
            </text>
          </svg>

          <div
            style={{
              position: "absolute",
              bottom: 12,
              left: 12,
              display: "flex",
              gap: 12,
              alignItems: "center",
              background: "var(--bg-2)",
              padding: "6px 10px",
              border: "1px solid var(--line-2)",
            }}
          >
            <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
              Severity
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <Dot tone="red" /> <span style={{ fontSize: 10 }}>≥75</span>
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <Dot tone="amber" /> <span style={{ fontSize: 10 }}>50–74</span>
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <Dot tone="ink" /> <span style={{ fontSize: 10 }}>&lt;50</span>
            </span>
          </div>
        </div>

        <div
          className="col"
          style={{
            width: 320,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          {sel && (
            <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
              <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                SELECTED · {sel.country} · {sel.id.toUpperCase()}
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: "var(--ink-0)",
                  marginTop: 4,
                  fontWeight: 500,
                  lineHeight: 1.3,
                }}
              >
                {sel.label}
              </div>
              <div className="row gap-2" style={{ marginTop: 8 }}>
                <Chip tone="amber">{sel.topic}</Chip>
                <Chip>SEV {(sel.severity * 100).toFixed(0)}</Chip>
              </div>
              <div style={{ marginTop: 10 }}>
                <KV k="Lat / Lon" v={`${sel.lat.toFixed(2)}° / ${sel.lon.toFixed(2)}°`} />
                <KV k="First seen" v="−42m" />
                <KV k="Sources" v="14" />
                <KV k="Goldstein tone" v="−7.2" vColor="var(--red)" />
              </div>
              <div className="col gap-2" style={{ marginTop: 12 }}>
                <Btn
                  primary
                  onClick={() => {
                    setTopic(`What happens next at ${sel.label}?`);
                    router.push("/ops");
                  }}
                >
                  ▸ DEBATE THIS PIN
                </Btn>
                <div className="row gap-2">
                  <Btn ghost>+ BOOKMARK</Btn>
                  <Btn ghost>↗ KG</Btn>
                </div>
              </div>
            </div>
          )}

          <Panel
            id="H"
            title="Hotspots"
            sub="ranked · 24h"
            style={{ flex: 1, border: "none", borderTop: "1px solid var(--line-2)" }}
          >
            <div className="col">
              {D.HOTSPOTS.map((h) => (
                <div
                  key={h.rank}
                  style={{
                    padding: "8px 12px",
                    borderBottom: "1px solid var(--line-1)",
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                  }}
                >
                  <span
                    className="tab amber"
                    style={{ fontSize: 11, minWidth: 16 }}
                  >
                    {String(h.rank).padStart(2, "0")}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, color: "var(--ink-0)" }}>{h.label}</div>
                    <div style={{ fontSize: 10, color: "var(--ink-2)" }}>
                      {h.events24h.toLocaleString()} events
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div
                      className="tab"
                      style={{
                        fontSize: 10,
                        color: h.delta.startsWith("+") ? "var(--green)" : "var(--red)",
                      }}
                    >
                      {h.delta}
                    </div>
                    <Bar value={h.severity} width={50} color="var(--amber)" />
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <div
        style={{
          height: 36,
          borderTop: "1px solid var(--line-2)",
          background: "var(--bg-1)",
          display: "flex",
          alignItems: "center",
          padding: "0 12px",
          gap: 12,
          flexShrink: 0,
        }}
      >
        <Btn ghost>◀</Btn>
        <Btn ghost>▶</Btn>
        <span className="muted tt-up" style={{ fontSize: 9 }}>
          −24h
        </span>
        <div style={{ flex: 1, position: "relative", height: 4, background: "var(--bg-3)" }}>
          <div style={{ width: "73%", height: "100%", background: "var(--amber)" }} />
          <div
            style={{
              position: "absolute",
              left: "73%",
              top: -4,
              width: 2,
              height: 12,
              background: "var(--ink-0)",
            }}
          />
        </div>
        <span className="muted tt-up" style={{ fontSize: 9 }}>
          NOW
        </span>
        <span className="tab amber" style={{ fontSize: 10 }}>
          14:22:08Z
        </span>
      </div>
    </div>
  );
}
