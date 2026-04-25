"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Bar } from "@/components/ui/Bar";
import { Btn } from "@/components/ui/Btn";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { api, type ClaimSummary } from "@/lib/api";
import { ARGUS_DATA, type RecentDebate } from "@/mock/data";

const EXTRA: RecentDebate[] = [
  { id: "d-2026-04-19-04", title: "Meta-EU AI Act: §50 enforcement first-mover", time: "6d", personas: 5, status: "done" },
  { id: "d-2026-04-18-01", title: "Brazil rate cut: BCB orthodoxy under fiscal stress", time: "7d", personas: 4, status: "done" },
  { id: "d-2026-04-17-02", title: "Iran-Israel: shadow war calibration", time: "8d", personas: 6, status: "done" },
  { id: "d-2026-04-15-03", title: "Taiwan preparedness: civil-defense reforms", time: "10d", personas: 5, status: "done" },
  { id: "d-2026-04-12-04", title: "ECB September: cut vs. hold", time: "13d", personas: 4, status: "done" },
  { id: "d-2026-04-10-01", title: "Ukraine peace deal: territorial freeze scenarios", time: "15d", personas: 6, status: "done" },
];

const COLLECTIONS: { n: string; c: number; sel?: boolean }[] = [
  { n: "All debates", c: 14, sel: true },
  { n: "★ Starred", c: 4 },
  { n: "Indo-Pacific", c: 12 },
  { n: "Macro", c: 8 },
  { n: "AI policy", c: 5 },
  { n: "Climate", c: 3 },
  { n: "Recurring", c: 2 },
];

// Deterministic hash so star/confidence don't reshuffle on re-render.
function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function LibraryScreen() {
  const router = useRouter();
  const [q, setQ] = useState("");

  // Live-wire to /claims when API is reachable. Mock list is the canonical view today;
  // claims are surfaced in a footer line. Falls through silently if API is offline.
  const claims = useQuery({
    queryKey: ["claims"],
    queryFn: api.claims,
    retry: 0,
  });

  const items = useMemo(() => [...ARGUS_DATA.RECENT, ...EXTRA], []);
  const filtered = q ? items.filter((i) => i.title.toLowerCase().includes(q.toLowerCase())) : items;

  return (
    <div className="col grow" style={{ overflow: "hidden" }}>
      <ScreenHeader
        code="08·LIBRARY"
        title="Synthesis Library"
        breadcrumb={`// ${items.length} archived · 14 collections${
          claims.isSuccess ? ` · ${(claims.data as ClaimSummary[]).length} live claims` : ""
        }`}
        right={
          <div className="row gap-2">
            <Btn ghost>+ COLLECTION</Btn>
            <Btn ghost>↗ BULK EXPORT</Btn>
            <Btn ghost>◫ DIFF TWO</Btn>
          </div>
        }
      />
      <div className="row grow" style={{ overflow: "hidden" }}>
        <div
          style={{
            width: 220,
            borderRight: "1px solid var(--line-2)",
            background: "var(--bg-1)",
            padding: 14,
            overflowY: "auto",
          }}
        >
          <div className="tt-up" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 6 }}>
            COLLECTIONS
          </div>
          {COLLECTIONS.map((c, i) => (
            <div
              key={i}
              style={{
                padding: "5px 8px",
                display: "flex",
                fontSize: 11,
                color: c.sel ? "var(--amber)" : "var(--ink-1)",
                background: c.sel ? "var(--bg-3)" : "transparent",
                cursor: "pointer",
                borderLeft: c.sel ? "2px solid var(--amber)" : "2px solid transparent",
              }}
            >
              <span style={{ flex: 1 }}>{c.n}</span>
              <span className="tab muted">{c.c}</span>
            </div>
          ))}
          <div
            className="tt-up"
            style={{ fontSize: 9, color: "var(--ink-3)", margin: "16px 0 6px" }}
          >
            FILTERS
          </div>
          <div className="col gap-1" style={{ fontSize: 10 }}>
            <div>· By topic</div>
            <div>· By persona</div>
            <div>· By date range</div>
            <div>· By region</div>
            <div>· By confidence</div>
          </div>
        </div>
        <div className="grow col" style={{ overflow: "hidden" }}>
          <div
            style={{
              padding: 12,
              borderBottom: "1px solid var(--line-2)",
              background: "var(--bg-1)",
            }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="input"
              placeholder="search debates · regex supported"
            />
          </div>
          <div className="grow" style={{ overflowY: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 24 }}></th>
                  <th>Title</th>
                  <th style={{ width: 80 }}>ID</th>
                  <th style={{ width: 70 }}>Personas</th>
                  <th style={{ width: 90 }}>Confidence</th>
                  <th style={{ width: 70 }}>Status</th>
                  <th style={{ width: 60 }}>Age</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => {
                  const seed = hash(d.id);
                  const star = seed % 10 < 3;
                  const conf = 0.5 + ((seed % 40) / 100);
                  return (
                    <tr
                      key={d.id}
                      onClick={() =>
                        router.push(d.status === "running" ? "/debate" : "/synthesis")
                      }
                      style={{ cursor: "pointer" }}
                    >
                      <td>{star ? "★" : ""}</td>
                      <td style={{ color: "var(--ink-0)" }}>{d.title}</td>
                      <td className="tab muted">{d.id}</td>
                      <td className="tab">{d.personas}</td>
                      <td>
                        <Bar value={conf} width={70} color="var(--amber)" />
                      </td>
                      <td>
                        <span
                          className="tt-up"
                          style={{
                            fontSize: 9,
                            color: d.status === "running" ? "var(--amber)" : "var(--green)",
                          }}
                        >
                          {d.status}
                        </span>
                      </td>
                      <td className="tab muted">{d.time}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
