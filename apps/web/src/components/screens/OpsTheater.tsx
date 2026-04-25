"use client";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";
import { KV } from "@/components/ui/KV";
import { Panel } from "@/components/ui/Panel";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Segmented } from "@/components/ui/Segmented";
import { api, type DiscussionListItem, type DiscussionStatus } from "@/lib/api";

type Filter = "all" | "in_flight" | "completed" | "failed";

const PAGE_SIZE = 50;
const POLL_MS = 5000;

const IN_FLIGHT_STATUSES: ReadonlySet<DiscussionStatus> = new Set([
  "planning",
  "researching",
  "debating",
  "synthesizing",
]);

function isInFlight(status: DiscussionStatus): boolean {
  return !["completed", "failed"].includes(status);
}

function statusTone(status: DiscussionStatus): "amber" | "green" | "red" | "default" {
  if (status === "completed") return "green";
  if (status === "failed") return "red";
  if (IN_FLIGHT_STATUSES.has(status)) return "amber";
  // unknown / future statuses (e.g. criticizing) — treat as in-flight amber
  return "amber";
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

function relTime(iso: string): string {
  const d = new Date(iso).getTime();
  if (!Number.isFinite(d)) return "—";
  const s = (Date.now() - d) / 1000;
  if (s < 60) return `${Math.floor(s)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export function OpsTheater() {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>("all");

  const discussions = useQuery({
    queryKey: ["discussions", "ops", filter],
    queryFn: () => api.discussions({ limit: PAGE_SIZE }),
    refetchInterval: POLL_MS,
    refetchOnWindowFocus: true,
    staleTime: 0,
    placeholderData: keepPreviousData,
    retry: 0,
  });

  const all: DiscussionListItem[] = discussions.data?.items ?? [];

  const stats = useMemo(() => {
    let inFlight = 0;
    let completed = 0;
    let failed = 0;
    for (const d of all) {
      if (d.status === "completed") completed++;
      else if (d.status === "failed") failed++;
      else if (isInFlight(d.status)) inFlight++;
    }
    return { total: all.length, inFlight, completed, failed };
  }, [all]);

  const filtered = useMemo(() => {
    if (filter === "all") return all;
    if (filter === "in_flight") return all.filter((d) => isInFlight(d.status));
    if (filter === "completed") return all.filter((d) => d.status === "completed");
    if (filter === "failed") return all.filter((d) => d.status === "failed");
    return all;
  }, [all, filter]);

  const apiOnline = discussions.isSuccess;
  const hasInFlight = stats.inFlight > 0;

  const headerRight = (
    <div className="row gap-2" style={{ alignItems: "center" }}>
      <Dot tone={hasInFlight ? "amber" : apiOnline ? "green" : "ink"} pulse={hasInFlight} />
      <span className="tt-up muted" style={{ fontSize: 9 }}>
        {discussions.isLoading
          ? "loading..."
          : discussions.isError
            ? "api offline"
            : hasInFlight
              ? `${stats.inFlight} in-flight · live`
              : "idle · live"}
      </span>
    </div>
  );

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="F4 / OPS"
        title="Operations Theater"
        breadcrumb={`// ${all.length} runs · refresh ${POLL_MS / 1000}s`}
        right={headerRight}
      />

      <div
        className="row gap-3"
        style={{
          padding: "10px 16px",
          borderBottom: "1px solid var(--line-2)",
          background: "var(--bg-1)",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <span className="tt-up muted" style={{ fontSize: 9 }}>
          Filter
        </span>
        <Segmented<Filter>
          options={[
            { value: "all", label: "All" },
            { value: "in_flight", label: "In-flight" },
            { value: "completed", label: "Completed" },
            { value: "failed", label: "Failed" },
          ]}
          value={filter}
          onChange={setFilter}
        />
        <div style={{ flex: 1 }} />
        <span className="tt-up muted" style={{ fontSize: 9 }}>
          Showing {filtered.length} / {all.length}
        </span>
      </div>

      <div
        className="row gap-3"
        style={{
          padding: "10px 16px",
          borderBottom: "1px solid var(--line-2)",
          background: "var(--bg-0)",
          flexShrink: 0,
        }}
      >
        <Panel style={{ flex: 1, padding: "8px 12px" }}>
          <KV k="Total · last 50" v={stats.total} />
        </Panel>
        <Panel style={{ flex: 1, padding: "8px 12px" }}>
          <KV
            k="In-flight"
            v={stats.inFlight}
            vColor={stats.inFlight > 0 ? "var(--amber)" : "var(--ink-2)"}
          />
        </Panel>
        <Panel style={{ flex: 1, padding: "8px 12px" }}>
          <KV
            k="Completed"
            v={stats.completed}
            vColor={stats.completed > 0 ? "var(--green)" : "var(--ink-2)"}
          />
        </Panel>
        <Panel style={{ flex: 1, padding: "8px 12px" }}>
          <KV
            k="Failed"
            v={stats.failed}
            vColor={stats.failed > 0 ? "var(--red)" : "var(--ink-2)"}
          />
        </Panel>
      </div>

      <div className="grow" style={{ overflowY: "auto" }}>
        {discussions.isLoading && all.length === 0 && (
          <div style={{ padding: 24, fontSize: 11, color: "var(--ink-3)" }}>
            loading discussions...
          </div>
        )}
        {discussions.isError && all.length === 0 && (
          <div style={{ padding: 24, fontSize: 11, color: "var(--red)" }}>
            ── api unreachable · retrying every {POLL_MS / 1000}s ──
          </div>
        )}
        {!discussions.isLoading && !discussions.isError && filtered.length === 0 && (
          <div
            style={{
              padding: 32,
              textAlign: "center",
              color: "var(--ink-3)",
              fontSize: 11,
            }}
          >
            ── no discussions match this filter ──
          </div>
        )}
        {filtered.length > 0 && (
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 32 }}></th>
                <th style={{ width: 90 }}>ID</th>
                <th>Topic</th>
                <th style={{ width: 110 }}>Vertical</th>
                <th style={{ width: 130 }}>Status</th>
                <th style={{ width: 70 }}>Started</th>
                <th style={{ width: 60 }}>Claims</th>
                <th style={{ width: 30 }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => {
                const inFlight = isInFlight(d.status);
                const tone = statusTone(d.status);
                const dotTone =
                  tone === "green" ? "green" : tone === "red" ? "red" : "amber";
                const claims = d.final_claim_count;
                return (
                  <tr
                    key={d.id}
                    onClick={() => router.push(`/debate?id=${d.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <Dot tone={dotTone} pulse={inFlight} />
                    </td>
                    <td className="tab muted" style={{ fontSize: 10 }}>
                      {d.id.slice(0, 8)}
                    </td>
                    <td style={{ color: "var(--ink-0)", lineHeight: 1.4 }}>
                      {truncate(d.topic, 60)}
                    </td>
                    <td>
                      <Chip tone="default">{d.vertical}</Chip>
                    </td>
                    <td>
                      <span
                        className="tt-up"
                        style={{
                          fontSize: 9,
                          color:
                            tone === "green"
                              ? "var(--green)"
                              : tone === "red"
                                ? "var(--red)"
                                : "var(--amber)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        {inFlight && <Dot tone="amber" pulse size={5} />}
                        {d.status}
                      </span>
                    </td>
                    <td className="tab muted" style={{ fontSize: 10 }}>
                      {relTime(d.started_at)}
                    </td>
                    <td className="tab">{claims}</td>
                    <td className="muted">→</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
