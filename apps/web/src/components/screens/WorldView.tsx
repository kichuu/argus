"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useState } from "react";
// Leaflet's CSS is required globally; import once at module top.
import "leaflet/dist/leaflet.css";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type SourcePin } from "@/lib/api";

// Next.js needs the dynamic + ssr:false because Leaflet touches `window` at import time.
const MapContainer = dynamic(
  () => import("react-leaflet").then((m) => m.MapContainer),
  { ssr: false },
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((m) => m.TileLayer),
  { ssr: false },
);
const CircleMarker = dynamic(
  () => import("react-leaflet").then((m) => m.CircleMarker),
  { ssr: false },
);
const Tooltip = dynamic(
  () => import("react-leaflet").then((m) => m.Tooltip),
  { ssr: false },
);

const TILE_URL =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>';

// Leaflet writes `stroke`/`fill` directly as SVG attributes which don't
// resolve CSS custom properties — match var(--amber) at the literal hex.
const PIN_COLOR = "#f5a524";

function pinRadius(sourceCount: number): number {
  return Math.max(5, Math.min(22, 5 + Math.log2(sourceCount + 1) * 2.5));
}

function relTime(iso: string | null): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (!Number.isFinite(ms)) return "—";
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function WorldView() {
  const [selectedPin, setSelectedPin] = useState<SourcePin | null>(null);

  // Refetch every 30s so the map updates as the ingestion loop pulls fresh data.
  const sources = useQuery<SourcePin[]>({
    queryKey: ["world", "sources"],
    queryFn: () => api.worldSources({ limit: 1000 }),
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 0,
  });

  const list = sources.data ?? [];
  const totalSources = list.reduce((acc, p) => acc + p.source_count, 0);

  const breadcrumb = sources.isError
    ? "// api offline"
    : sources.isLoading
      ? "// loading sources…"
      : `// ${list.length} location${list.length === 1 ? "" : "s"} · ${totalSources} sources · click pin for details`;

  return (
    <div className="col grow" style={{ overflow: "hidden", position: "relative" }}>
      {/* Header overlay (top-left, above map) */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 500,
          pointerEvents: "none",
        }}
      >
        <div style={{ pointerEvents: "auto" }}>
          <ScreenHeader
            code="02·WORLD"
            title="WorldView"
            breadcrumb={breadcrumb}
            right={
              <div className="row gap-2">
                <span
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-3)" }}
                >
                  WGS84 · OSM/CARTO · refresh 30s
                </span>
              </div>
            }
          />
        </div>
      </div>

      {/* Map fills the remaining space */}
      <div
        className="grow"
        style={{
          position: "relative",
          background: "var(--bg-0)",
          overflow: "hidden",
        }}
      >
        <MapContainer
          center={[20, 0]}
          zoom={2}
          minZoom={2}
          maxZoom={8}
          worldCopyJump
          scrollWheelZoom
          style={{
            width: "100%",
            height: "100%",
            background: "var(--bg-0)",
          }}
          attributionControl
        >
          <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
          {list.map((pin) => (
            <CircleMarker
              key={pin.location_key}
              center={[pin.lat, pin.lon]}
              radius={pinRadius(pin.source_count)}
              pathOptions={{
                color: PIN_COLOR,
                fillColor: PIN_COLOR,
                fillOpacity: 0.55,
                opacity: 0.9,
                weight: 1,
              }}
              eventHandlers={{ click: () => setSelectedPin(pin) }}
            >
              <Tooltip
                direction="top"
                offset={[0, -4]}
                opacity={1}
                className="argus-tooltip"
              >
                {pin.city} · {pin.source_count} src · {pin.publisher_count} pub
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Empty state overlay */}
        {!sources.isLoading && !sources.isError && list.length === 0 && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              pointerEvents: "none",
              zIndex: 400,
            }}
          >
            <div
              style={{
                background: "var(--bg-1)",
                border: "1px solid var(--line-2)",
                padding: "16px 22px",
                maxWidth: 480,
                pointerEvents: "auto",
              }}
            >
              <div
                className="tt-up"
                style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 6 }}
              >
                NO SOURCES
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--ink-0)",
                  lineHeight: 1.5,
                }}
              >
                No ingested sources yet. Run{" "}
                <span className="tab" style={{ color: "var(--amber)" }}>
                  uv run python -m scripts.run_ingestion
                </span>{" "}
                or start the continuous loop with{" "}
                <span className="tab" style={{ color: "var(--amber)" }}>
                  ./start.sh --with-ingest
                </span>{" "}
                to populate.
              </div>
            </div>
          </div>
        )}

        {/* Map legend (bottom-left) */}
        <div
          style={{
            position: "absolute",
            bottom: 12,
            left: 12,
            zIndex: 500,
            display: "flex",
            gap: 12,
            alignItems: "center",
            background: "var(--bg-2)",
            padding: "6px 10px",
            border: "1px solid var(--line-2)",
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          <span className="tt-up" style={{ fontSize: 9, color: "var(--ink-2)" }}>
            SOURCES
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Dot tone="amber" size={5} /> <span style={{ fontSize: 10 }}>1</span>
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Dot tone="amber" size={9} /> <span style={{ fontSize: 10 }}>10</span>
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Dot tone="amber" size={14} /> <span style={{ fontSize: 10 }}>100+</span>
          </span>
        </div>
      </div>

      {/* Side panel slides in from right when pin selected */}
      {selectedPin && (
        <div
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            bottom: 0,
            width: 400,
            background: "var(--bg-1)",
            borderLeft: "1px solid var(--line-2)",
            zIndex: 600,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            boxShadow: "-8px 0 24px rgba(0,0,0,0.4)",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: 14,
              borderBottom: "1px solid var(--line-2)",
              flexShrink: 0,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 8,
              }}
            >
              <div style={{ minWidth: 0, flex: 1 }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-3)" }}
                >
                  LOCATION · {selectedPin.country}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: "var(--ink-0)",
                    marginTop: 4,
                    fontWeight: 500,
                    lineHeight: 1.3,
                    wordBreak: "break-word",
                  }}
                >
                  {selectedPin.city}
                </div>
              </div>
              <Btn ghost onClick={() => setSelectedPin(null)}>
                ✕
              </Btn>
            </div>
            <div className="row gap-2" style={{ marginTop: 8, flexWrap: "wrap" }}>
              <Chip tone="amber">{selectedPin.source_count} sources</Chip>
              <Chip tone="default">{selectedPin.publisher_count} publishers</Chip>
              <span className="tt-up muted" style={{ fontSize: 9 }}>
                latest {relTime(selectedPin.latest_fetched_at)}
              </span>
            </div>
            <div style={{ marginTop: 10 }}>
              <KV
                k="Lat / Lon"
                v={`${selectedPin.lat.toFixed(3)}° / ${selectedPin.lon.toFixed(3)}°`}
              />
            </div>
          </div>

          {/* Publishers list */}
          <div
            style={{
              padding: "10px 14px",
              borderBottom: "1px solid var(--line-1)",
              background: "var(--bg-2)",
            }}
          >
            <div
              className="tt-up"
              style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
            >
              PUBLISHERS
            </div>
            <div className="row gap-1" style={{ flexWrap: "wrap" }}>
              {selectedPin.publishers.map((p) => (
                <span
                  key={p}
                  style={{
                    fontSize: 10,
                    color: "var(--ink-1)",
                    border: "1px solid var(--line-2)",
                    padding: "1px 6px",
                  }}
                >
                  {p}
                </span>
              ))}
            </div>
          </div>

          {/* Sample titles */}
          <div className="col grow" style={{ overflowY: "auto", minHeight: 0 }}>
            <div
              style={{
                padding: "10px 14px",
                borderBottom: "1px solid var(--line-1)",
                background: "var(--bg-2)",
                position: "sticky",
                top: 0,
                zIndex: 1,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                className="tt-up"
                style={{ fontSize: 9, color: "var(--ink-2)" }}
              >
                RECENT SOURCES
              </span>
              <span
                className="tab"
                style={{ fontSize: 10, color: "var(--ink-3)" }}
              >
                showing {selectedPin.sample_titles.length} of {selectedPin.source_count}
              </span>
            </div>
            {selectedPin.sample_titles.length === 0 ? (
              <div
                style={{
                  padding: 14,
                  fontSize: 11,
                  color: "var(--ink-3)",
                }}
              >
                ── no titles ──
              </div>
            ) : (
              selectedPin.sample_titles.map((title, i) => (
                <div
                  key={i}
                  style={{
                    padding: "8px 14px",
                    borderBottom: "1px solid var(--line-1)",
                    fontSize: 12,
                    color: "var(--ink-0)",
                    lineHeight: 1.45,
                  }}
                >
                  {title}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
