"use client";
import { useQuery } from "@tanstack/react-query";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { useEffect, useMemo, useRef, useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { MockBadge } from "@/components/ui/MockBadge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type RelationSummary } from "@/lib/api";
import { apiStatus } from "@/lib/api-status";

const W = 800;
const H = 600;

const TYPE_COLOR: Record<string, string> = {
  country: "var(--p-1)",
  person: "var(--p-2)",
  company: "var(--p-4)",
  org: "var(--p-3)",
  event: "var(--p-5)",
  doc: "var(--p-6)",
  asset: "var(--p-7)",
  place: "var(--ink-1)",
};

const FILTERS = ["all", "country", "person", "org", "company", "event", "place", "doc", "asset"] as const;

type GraphNode = SimulationNodeDatum & {
  id: string;
  label: string;
  type: string;
  degree: number;
};

type GraphLink = SimulationLinkDatum<GraphNode> & {
  relation: string;
  source: string | GraphNode;
  target: string | GraphNode;
};

type LaidOutGraph = {
  nodes: GraphNode[];
  links: GraphLink[];
};

export function KGScreen() {
  const entitiesQuery = useQuery({
    queryKey: ["entities"],
    queryFn: api.entities,
    retry: 0,
    staleTime: 30_000,
  });

  const status = apiStatus(entitiesQuery);
  const apiOnline = status.online;

  const [filter, setFilter] = useState<string>("all");
  const [selId, setSelId] = useState<string | null>(null);

  // Stable list of (id, label, type) before relations / layout.
  const baseEntities = useMemo(() => {
    if (!entitiesQuery.data) return [] as { id: string; label: string; type: string }[];
    return entitiesQuery.data.map((e) => ({
      id: e.id,
      label: e.canonical_name ?? e.name ?? e.id,
      type: (e.type ?? "place").toLowerCase(),
    }));
  }, [entitiesQuery.data]);

  const effectiveSelId = selId ?? baseEntities[0]?.id ?? null;

  // Pull relations for the *selected* entity to draw real edges in the panel.
  const relationsQuery = useQuery({
    queryKey: ["entity-relations", effectiveSelId],
    queryFn: () => api.entityRelations(effectiveSelId as string),
    enabled: apiOnline && !!effectiveSelId,
    retry: 0,
    staleTime: 30_000,
  });

  // For the global layout, also pull relations for each visible entity. We
  // batch via a single useMemo over the relationsQuery — for now we only have
  // the selected entity's relations, so we use those plus self-links to keep
  // the simulation stable. (Backend doesn't expose a /relations bulk endpoint.)
  const knownRelations: RelationSummary[] = relationsQuery.data ?? [];

  // The graph the layout simulates: filter applied to nodes, then edges
  // restricted to surviving nodes.
  const filteredEntities = useMemo(
    () =>
      filter === "all"
        ? baseEntities
        : baseEntities.filter((e) => e.type === filter),
    [filter, baseEntities],
  );

  // Compute degree from currently known relations (selected node's links).
  const degreeMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of knownRelations) {
      m.set(r.subject_id, (m.get(r.subject_id) ?? 0) + 1);
      m.set(r.object_id, (m.get(r.object_id) ?? 0) + 1);
    }
    return m;
  }, [knownRelations]);

  // Force-directed layout state — recomputed when entities/relations change.
  const [layout, setLayout] = useState<LaidOutGraph>({ nodes: [], links: [] });
  const layoutKey = useRef<string>("");

  useEffect(() => {
    if (filteredEntities.length === 0) {
      // Guard against re-running setState every render when input is empty.
      if (layoutKey.current !== "") {
        setLayout({ nodes: [], links: [] });
        layoutKey.current = "";
      }
      return;
    }

    const idSet = new Set(filteredEntities.map((e) => e.id));
    const links: GraphLink[] = knownRelations
      .filter((r) => idSet.has(r.subject_id) && idSet.has(r.object_id))
      .map((r) => ({
        source: r.subject_id,
        target: r.object_id,
        relation: r.relation_type,
      }));

    const nodes: GraphNode[] = filteredEntities.map((e) => ({
      id: e.id,
      label: e.label,
      type: e.type,
      degree: degreeMap.get(e.id) ?? 0,
    }));

    // Memoize on a key so we don't re-simulate on every render.
    const key = `${nodes.length}:${links.length}:${nodes.map((n) => n.id).join(",")}`;
    if (key === layoutKey.current) return;
    layoutKey.current = key;

    const sim = forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        forceLink<GraphNode, GraphLink>(links)
          .id((n) => n.id)
          .distance(80)
          .strength(0.6),
      )
      .force("charge", forceManyBody<GraphNode>().strength(-180))
      .force(
        "collide",
        forceCollide<GraphNode>().radius((n) => 6 + Math.sqrt(Math.max(n.degree, 1)) * 2.2),
      )
      .force("center", forceCenter(W / 2, H / 2))
      .stop();

    // Run synchronously: ~300 ticks is enough for stable layouts at this scale.
    const ticks = Math.min(
      300,
      Math.ceil(Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay())),
    );
    for (let i = 0; i < ticks; i++) sim.tick();

    // Clamp into the visible canvas with a margin so labels aren't cut off.
    const margin = 40;
    for (const n of nodes) {
      n.x = Math.max(margin, Math.min(W - margin, n.x ?? W / 2));
      n.y = Math.max(margin, Math.min(H - margin, n.y ?? H / 2));
    }

    setLayout({ nodes, links });
  }, [filteredEntities, knownRelations, degreeMap]);

  const sel = layout.nodes.find((n) => n.id === effectiveSelId) ?? layout.nodes[0] ?? null;
  const selDegree = sel ? degreeMap.get(sel.id) ?? 0 : 0;

  const breadcrumb = entitiesQuery.isLoading
    ? "// loading entities…"
    : apiOnline
      ? `// ${baseEntities.length} entities · ${knownRelations.length} relations on selection`
      : "// api offline";

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="03·KG"
        title="Knowledge Graph Explorer"
        breadcrumb={breadcrumb}
        right={
          <div className="row gap-2" style={{ alignItems: "center" }}>
            <MockBadge online={apiOnline} loading={status.loading} />
            <Segmented size="sm" options={FILTERS} value={filter} onChange={setFilter} />
            <Btn ghost>↗ EXPORT</Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          className="grow grid-bg"
          style={{ position: "relative", overflow: "hidden", background: "var(--bg-1)" }}
        >
          {entitiesQuery.isLoading ? (
            <Skeleton rows={6} rowHeight={32} gap={10} style={{ margin: 24 }} />
          ) : entitiesQuery.isError ? (
            <ErrorBox
              message="failed to load entities"
              onRetry={() => entitiesQuery.refetch()}
              style={{ margin: 24 }}
            />
          ) : baseEntities.length === 0 ? (
            <EmptyState
              title="No entities extracted yet"
              hint="Ingest sources and run discussions to populate the graph."
              style={{ margin: 24 }}
            />
          ) : (
            <svg
              viewBox={`0 0 ${W} ${H}`}
              style={{ width: "100%", height: "100%" }}
              preserveAspectRatio="xMidYMid meet"
            >
              {layout.links.map((l, i) => {
                const a =
                  typeof l.source === "string"
                    ? layout.nodes.find((n) => n.id === l.source)
                    : (l.source as GraphNode);
                const b =
                  typeof l.target === "string"
                    ? layout.nodes.find((n) => n.id === l.target)
                    : (l.target as GraphNode);
                if (!a || !b || a.x == null || b.x == null) return null;
                const isSel = sel && (sel.id === a.id || sel.id === b.id);
                return (
                  <g key={i}>
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke={isSel ? "var(--amber)" : "var(--line-2)"}
                      strokeWidth={isSel ? 1 : 0.5}
                      opacity={isSel ? 0.9 : 0.5}
                    />
                    {isSel && (
                      <text
                        x={((a.x ?? 0) + (b.x ?? 0)) / 2}
                        y={((a.y ?? 0) + (b.y ?? 0)) / 2 - 3}
                        fontSize="8"
                        fill="var(--amber)"
                        fontFamily="JetBrains Mono"
                        textAnchor="middle"
                      >
                        {l.relation}
                      </text>
                    )}
                  </g>
                );
              })}
              {layout.nodes.map((n) => {
                const cx = n.x ?? W / 2;
                const cy = n.y ?? H / 2;
                const isSel = sel?.id === n.id;
                const r = 4 + Math.sqrt(Math.max(n.degree, 1)) * 1.8;
                const c = TYPE_COLOR[n.type] || "var(--ink-1)";
                return (
                  <g
                    key={n.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelId(n.id)}
                  >
                    {isSel && <circle cx={cx} cy={cy} r={r + 8} fill={c} opacity="0.18" />}
                    <circle
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill="var(--bg-1)"
                      stroke={c}
                      strokeWidth={isSel ? 2 : 1}
                    />
                    <circle cx={cx} cy={cy} r={r / 2} fill={c} />
                    <text
                      x={cx + r + 5}
                      y={cy + 3}
                      fontSize="9"
                      fill={isSel ? "var(--ink-0)" : "var(--ink-1)"}
                      fontFamily="JetBrains Mono"
                    >
                      {n.label}
                    </text>
                  </g>
                );
              })}
              <text x={10} y={18} fontFamily="JetBrains Mono" fontSize="9" fill="var(--ink-3)">
                FORCE-DIRECTED · LIVE ENTITIES
              </text>
            </svg>
          )}

          {layout.nodes.length > 0 && (
            <div
              style={{
                position: "absolute",
                bottom: 12,
                left: 12,
                background: "var(--bg-2)",
                border: "1px solid var(--line-2)",
                padding: "6px 10px",
                display: "flex",
                gap: 12,
                fontSize: 9,
                flexWrap: "wrap",
                maxWidth: "90%",
              }}
            >
              {Object.entries(TYPE_COLOR).map(([k, c]) => (
                <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                  <span
                    style={{ width: 6, height: 6, borderRadius: "50%", background: c }}
                  />{" "}
                  <span className="tt-up" style={{ color: "var(--ink-2)" }}>
                    {k}
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>

        <div
          style={{
            width: 320,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          {sel ? (
            <>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)" }}>
                  {sel.type}
                </div>
                <div
                  style={{
                    fontSize: 16,
                    color: "var(--ink-0)",
                    marginTop: 2,
                    fontWeight: 600,
                  }}
                >
                  {sel.label}
                </div>
                <div className="row gap-2" style={{ marginTop: 8 }}>
                  <Chip tone="amber">deg {selDegree}</Chip>
                </div>
              </div>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                >
                  RELATIONS{" "}
                  {relationsQuery.data ? `(${relationsQuery.data.length})` : ""}
                </div>
                {relationsQuery.isLoading ? (
                  <div className="muted" style={{ fontSize: 10 }}>
                    loading...
                  </div>
                ) : relationsQuery.isError ? (
                  <ErrorBox
                    message="failed to load relations"
                    onRetry={() => relationsQuery.refetch()}
                  />
                ) : (relationsQuery.data?.length ?? 0) === 0 ? (
                  <div className="muted" style={{ fontSize: 10 }}>
                    no relations
                  </div>
                ) : (
                  relationsQuery.data!.map((r) => {
                    const otherId =
                      r.subject_id === sel.id ? r.object_id : r.subject_id;
                    const other =
                      layout.nodes.find((n) => n.id === otherId) ??
                      baseEntities.find((b) => b.id === otherId);
                    const dir = r.subject_id === sel.id ? "→" : "←";
                    return (
                      <div
                        key={r.id}
                        className="row gap-3"
                        style={{ padding: "4px 0", fontSize: 10 }}
                      >
                        <span
                          className="tab amber"
                          style={{ minWidth: 70, fontSize: 9 }}
                        >
                          {dir} {r.relation_type}
                        </span>
                        <span style={{ color: "var(--ink-1)", flex: 1 }}>
                          {other?.label ?? otherId}
                        </span>
                        {typeof r.confidence === "number" && (
                          <span className="muted tab" style={{ fontSize: 9 }}>
                            {r.confidence.toFixed(2)}
                          </span>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            <div style={{ padding: 14 }}>
              <div className="muted" style={{ fontSize: 10 }}>
                Select a node to inspect.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
