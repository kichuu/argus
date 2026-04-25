"use client";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { KV } from "@/components/ui/KV";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { api, type Entity, type EntityRelation, type EntityType } from "@/lib/api";

// TODO(graph-viz): swap this list view for a React Flow / Cytoscape force-directed
// graph once node/edge counts and persistence story stabilise. For now we render a
// grouped, filterable table — same data, easier to ship.

const FILTERS: { value: EntityType | "all"; label: string }[] = [
  { value: "all", label: "ALL" },
  { value: "person", label: "PERSON" },
  { value: "org", label: "ORG" },
  { value: "place", label: "PLACE" },
  { value: "event", label: "EVENT" },
  { value: "policy", label: "POLICY" },
  { value: "product", label: "PRODUCT" },
  { value: "concept", label: "CONCEPT" },
];

const TYPE_COLOR: Record<EntityType, string> = {
  person: "var(--p-2)",
  org: "var(--p-3)",
  place: "var(--p-1)",
  event: "var(--p-5)",
  policy: "var(--p-6)",
  product: "var(--p-4)",
  concept: "var(--p-7)",
};

export function KGScreen() {
  const [filter, setFilter] = useState<EntityType | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const entities = useQuery<Entity[]>({
    queryKey: ["entities", { filter }],
    queryFn: () =>
      api.entities({
        limit: 200,
        ...(filter !== "all" ? { entity_type: filter } : {}),
      }),
    retry: 0,
  });

  const relations = useQuery<EntityRelation[]>({
    queryKey: ["entity-relations", selectedId],
    queryFn: () => api.entityRelations(selectedId!, { limit: 100 }),
    enabled: !!selectedId,
    retry: 0,
  });

  const list = entities.data ?? [];
  const selected = useMemo(() => list.find((e) => e.id === selectedId) ?? null, [list, selectedId]);

  // Group by entity_type for stable visual grouping.
  const groups = useMemo(() => {
    const m = new Map<EntityType, Entity[]>();
    for (const e of list) {
      const arr = m.get(e.entity_type) ?? [];
      arr.push(e);
      m.set(e.entity_type, arr);
    }
    return Array.from(m.entries());
  }, [list]);

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="03·KG"
        title="Knowledge Graph Explorer"
        breadcrumb={
          entities.isError
            ? `// api offline`
            : `// ${list.length} entit${list.length === 1 ? "y" : "ies"} · list view (graph viz pending)`
        }
        right={
          <div className="row gap-2">
            <Segmented
              size="sm"
              options={FILTERS}
              value={filter}
              onChange={(v) => {
                setFilter(v);
                setSelectedId(null);
              }}
            />
            <Btn ghost>↗ EXPORT</Btn>
          </div>
        }
      />

      <div className="row grow" style={{ overflow: "hidden" }}>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div className="grow" style={{ overflowY: "auto" }}>
            {entities.isLoading && (
              <div style={{ padding: 24, fontSize: 11, color: "var(--ink-3)" }}>
                loading entities...
              </div>
            )}
            {entities.isError && (
              <div style={{ padding: 24, fontSize: 11, color: "var(--red)" }}>
                ⚠ failed to fetch entities: {String(entities.error)}
              </div>
            )}
            {!entities.isLoading && !entities.isError && groups.length === 0 && (
              <div style={{ padding: 24, fontSize: 11, color: "var(--ink-3)" }}>
                ── no entities ──
              </div>
            )}
            {groups.map(([type, ents]) => (
              <div key={type}>
                <div
                  className="tt-up"
                  style={{
                    padding: "6px 14px",
                    fontSize: 9,
                    color: TYPE_COLOR[type],
                    background: "var(--bg-2)",
                    borderTop: "1px solid var(--line-2)",
                    borderBottom: "1px solid var(--line-1)",
                    letterSpacing: "0.12em",
                  }}
                >
                  {type} · {ents.length}
                </div>
                <table className="tbl">
                  <tbody>
                    {ents.map((e) => {
                      const isSel = e.id === selectedId;
                      return (
                        <tr
                          key={e.id}
                          onClick={() => setSelectedId(e.id)}
                          style={{
                            cursor: "pointer",
                            background: isSel ? "var(--bg-3)" : undefined,
                          }}
                        >
                          <td style={{ color: "var(--ink-0)", width: "40%" }}>
                            <span
                              style={{
                                display: "inline-block",
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                background: TYPE_COLOR[type],
                                marginRight: 8,
                                verticalAlign: "middle",
                              }}
                            />
                            {e.canonical_name}
                          </td>
                          <td className="muted" style={{ fontSize: 10 }}>
                            {e.aliases.length > 0 ? `aka ${e.aliases.slice(0, 3).join(", ")}` : ""}
                          </td>
                          <td className="tab muted" style={{ width: 110 }}>
                            {e.wikidata_id ?? "—"}
                          </td>
                          <td className="tab muted" style={{ width: 90 }}>
                            {e.id.slice(0, 8)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            width: 360,
            borderLeft: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            overflowY: "auto",
          }}
        >
          {!selected && (
            <div style={{ padding: 14, fontSize: 11, color: "var(--ink-3)" }}>
              ── select an entity to inspect ──
            </div>
          )}
          {selected && (
            <>
              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: TYPE_COLOR[selected.entity_type] }}
                >
                  {selected.entity_type}
                </div>
                <div
                  style={{
                    fontSize: 16,
                    color: "var(--ink-0)",
                    marginTop: 4,
                    fontWeight: 600,
                    lineHeight: 1.35,
                  }}
                >
                  {selected.canonical_name}
                </div>
                <div className="row gap-2" style={{ marginTop: 8, flexWrap: "wrap" }}>
                  {selected.wikidata_id && <Chip tone="amber">{selected.wikidata_id}</Chip>}
                  {selected.aliases.length > 0 && (
                    <Chip>+{selected.aliases.length} alias</Chip>
                  )}
                </div>
                {selected.description && (
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--ink-1)",
                      marginTop: 10,
                      lineHeight: 1.5,
                    }}
                  >
                    {selected.description}
                  </div>
                )}
              </div>

              <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                <KV k="ID" v={<span className="tab">{selected.id.slice(0, 12)}…</span>} />
                <KV k="Created" v={new Date(selected.created_at).toISOString().slice(0, 10)} />
                <KV k="Updated" v={new Date(selected.updated_at).toISOString().slice(0, 10)} />
              </div>

              {selected.aliases.length > 0 && (
                <div style={{ padding: 14, borderBottom: "1px solid var(--line-2)" }}>
                  <div
                    className="tt-up"
                    style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                  >
                    ALIASES
                  </div>
                  <div className="row gap-1" style={{ flexWrap: "wrap" }}>
                    {selected.aliases.map((a, i) => (
                      <Chip key={i}>{a}</Chip>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ padding: 14 }}>
                <div
                  className="tt-up"
                  style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 6 }}
                >
                  RELATIONS{" "}
                  {relations.data ? `(${relations.data.length})` : relations.isLoading ? "…" : ""}
                </div>
                {relations.isError && (
                  <div style={{ fontSize: 10, color: "var(--red)" }}>
                    failed to load relations
                  </div>
                )}
                {relations.data && relations.data.length === 0 && (
                  <div style={{ fontSize: 10, color: "var(--ink-3)" }}>
                    no relations recorded
                  </div>
                )}
                {relations.data?.map((r) => {
                  const outgoing = r.subject_id === selected.id;
                  const otherId = outgoing ? r.object_id : r.subject_id;
                  return (
                    <div
                      key={r.id}
                      style={{
                        fontSize: 10,
                        padding: "4px 0",
                        color: "var(--ink-1)",
                        lineHeight: 1.4,
                      }}
                    >
                      <span className="tt-up muted" style={{ marginRight: 6 }}>
                        {outgoing ? "→" : "←"}
                      </span>
                      <span className="tt-up" style={{ color: "var(--amber)" }}>
                        {r.relation_type}
                      </span>
                      <span className="tab muted" style={{ marginLeft: 6 }}>
                        {otherId.slice(0, 8)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
