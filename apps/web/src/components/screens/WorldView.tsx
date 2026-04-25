"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
// Leaflet's CSS is required globally; import once at module top.
import "leaflet/dist/leaflet.css";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type Claim, type PlacePin } from "@/lib/api";

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

function pinRadius(claimCount: number): number {
  return Math.max(4, Math.min(20, 4 + Math.log2(claimCount + 1) * 2));
}

const STATUS_TONE: Record<Claim["status"], "amber" | "green" | "red" | "default"> = {
  likely_true: "green",
  contested: "amber",
  unverified: "default",
  likely_false: "red",
};

function statusLabel(s: Claim["status"]): string {
  switch (s) {
    case "likely_true":
      return "TRUE";
    case "contested":
      return "CONTESTED";
    case "unverified":
      return "UNVERIFIED";
    case "likely_false":
      return "FALSE";
  }
}

export function WorldView() {
  const [selectedPin, setSelectedPin] = useState<PlacePin | null>(null);

  const places = useQuery<PlacePin[]>({
    queryKey: ["world", "places"],
    queryFn: () => api.worldPlaces({ limit: 500 }),
    staleTime: 60_000,
    retry: 0,
  });

  // No `affected_entities` filter on /claims; fetch a wide page and filter
  // client-side by the selected pin's entity_id.
  const claims = useQuery<Claim[]>({
    queryKey: ["world", "claims-pool"],
    queryFn: () => api.claims({ limit: 100 }),
    staleTime: 60_000,
    retry: 0,
    enabled: !!selectedPin,
  });

  const list = places.data ?? [];

  const claimsForPin = useMemo<Claim[]>(() => {
    if (!selectedPin || !claims.data) return [];
    return claims.data.filter((c) =>
      c.affected_entities.includes(selectedPin.entity_id),
    );
  }, [selectedPin, claims.data]);

  const breadcrumb = places.isError
    ? "// api offline"
    : places.isLoading
      ? "// loading places…"
      : `// ${list.length} places · click pin for claims`;

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
                  WGS84 · OSM/CARTO
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
              key={pin.entity_id}
              center={[pin.lat, pin.lon]}
              radius={pinRadius(pin.claim_count)}
              pathOptions={{
                color: PIN_COLOR,
                fillColor: PIN_COLOR,
                fillOpacity: 0.6,
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
                {pin.name} · {pin.claim_count} claims
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Empty state overlay */}
        {!places.isLoading && !places.isError && list.length === 0 && (
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
                NO DATA
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--ink-0)",
                  lineHeight: 1.5,
                }}
              >
                No geocoded places yet — run{" "}
                <span className="tab" style={{ color: "var(--amber)" }}>
                  uv run python scripts/geocode_entities.py
                </span>{" "}
                to backfill coordinates from Wikidata.
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
            CLAIMS
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Dot tone="amber" size={4} /> <span style={{ fontSize: 10 }}>1</span>
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Dot tone="amber" size={8} /> <span style={{ fontSize: 10 }}>10</span>
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Dot tone="amber" size={12} /> <span style={{ fontSize: 10 }}>100+</span>
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
                  PLACE · {selectedPin.entity_id.slice(0, 8).toUpperCase()}
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
                  {selectedPin.name}
                </div>
              </div>
              <Btn ghost onClick={() => setSelectedPin(null)}>
                ✕
              </Btn>
            </div>
            <div className="row gap-2" style={{ marginTop: 8 }}>
              <Chip tone="amber">{selectedPin.claim_count} claims</Chip>
              {selectedPin.wikidata_id && (
                <a
                  href={`https://www.wikidata.org/wiki/${selectedPin.wikidata_id}`}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="chip"
                  style={{ textDecoration: "none" }}
                >
                  ↗ {selectedPin.wikidata_id}
                </a>
              )}
            </div>
            <div style={{ marginTop: 10 }}>
              <KV
                k="Lat / Lon"
                v={`${selectedPin.lat.toFixed(3)}° / ${selectedPin.lon.toFixed(3)}°`}
              />
              <KV k="Entity ID" v={selectedPin.entity_id.slice(0, 12) + "…"} />
            </div>
          </div>

          {/* Claims list */}
          <div
            className="col grow"
            style={{ overflowY: "auto", minHeight: 0 }}
          >
            <div
              style={{
                padding: "10px 14px",
                borderBottom: "1px solid var(--line-1)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--bg-2)",
                position: "sticky",
                top: 0,
                zIndex: 1,
              }}
            >
              <span
                className="tt-up"
                style={{ fontSize: 9, color: "var(--ink-2)" }}
              >
                CLAIMS MENTIONING THIS PLACE
              </span>
              <span
                className="tab"
                style={{ fontSize: 10, color: "var(--ink-3)" }}
              >
                {claims.isLoading ? "…" : claimsForPin.length}
              </span>
            </div>

            {claims.isLoading && (
              <div
                style={{
                  padding: 14,
                  fontSize: 11,
                  color: "var(--ink-2)",
                }}
              >
                Loading claims…
              </div>
            )}

            {claims.isError && (
              <div
                style={{
                  padding: 14,
                  fontSize: 11,
                  color: "var(--red)",
                }}
              >
                Failed to load claims (api offline)
              </div>
            )}

            {!claims.isLoading &&
              !claims.isError &&
              claimsForPin.length === 0 && (
                <div
                  style={{
                    padding: 14,
                    fontSize: 11,
                    color: "var(--ink-2)",
                  }}
                >
                  No claims in current pool reference this place.
                </div>
              )}

            {claimsForPin.map((c) => (
              <div
                key={c.id}
                style={{
                  padding: "10px 14px",
                  borderBottom: "1px solid var(--line-1)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    gap: 6,
                    alignItems: "center",
                    marginBottom: 6,
                  }}
                >
                  <Chip tone={STATUS_TONE[c.status]}>
                    {statusLabel(c.status)}
                  </Chip>
                  <span
                    className="tab"
                    style={{ fontSize: 10, color: "var(--ink-3)" }}
                  >
                    conf {(c.confidence * 100).toFixed(0)}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--ink-0)",
                    lineHeight: 1.4,
                  }}
                >
                  {c.statement}
                </div>
                <div
                  style={{
                    marginTop: 6,
                    display: "flex",
                    gap: 10,
                    fontSize: 10,
                    color: "var(--ink-2)",
                  }}
                >
                  <span>
                    + {c.supporting_evidence.length} support
                  </span>
                  <span>− {c.contradicting_evidence.length} contra</span>
                  <span>
                    {c.agent_consensus.agree}/{c.agent_consensus.disagree}/
                    {c.agent_consensus.uncertain}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
