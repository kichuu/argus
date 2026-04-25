"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, type ActivityEvent } from "@/lib/api";
import { useUIStore } from "@/store/ui";

const KIND_GLYPH: Record<ActivityEvent["kind"], string> = {
  claim: "•",
  source: "↳",
  discussion: "▶",
};

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const diff = Math.max(0, Date.now() - then);
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function truncate(text: string, n = 64): string {
  if (text.length <= n) return text;
  return text.slice(0, n - 1).trimEnd() + "…";
}

export function NotifsPanel() {
  const open = useUIStore((s) => s.notifsOpen);
  const close = useUIStore((s) => s.closeNotifs);
  const router = useRouter();

  const q = useQuery({
    queryKey: ["activity"],
    queryFn: () => api.activity({ limit: 20 }),
    refetchInterval: 30_000,
    retry: 0,
    staleTime: 30_000,
    enabled: open,
  });

  if (!open) return null;

  const events = q.data?.events ?? [];

  return (
    <div onClick={close} style={{ position: "fixed", inset: 0, zIndex: 9000 }}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "absolute",
          top: 44,
          right: 56,
          width: 360,
          maxHeight: "calc(100vh - 80px)",
          overflowY: "auto",
          background: "var(--bg-2)",
          border: "1px solid var(--line-3)",
        }}
      >
        <div
          style={{
            padding: "8px 12px",
            borderBottom: "1px solid var(--line-2)",
            display: "flex",
            alignItems: "center",
            position: "sticky",
            top: 0,
            background: "var(--bg-2)",
            zIndex: 1,
          }}
        >
          <span className="tt-up" style={{ fontSize: 10, color: "var(--ink-1)", fontWeight: 600 }}>
            Activity
          </span>
          <div style={{ flex: 1 }} />
          {q.isSuccess && (
            <span className="muted tt-up" style={{ fontSize: 9 }}>
              {events.length} event{events.length === 1 ? "" : "s"}
            </span>
          )}
        </div>

        {q.isLoading && <Skeleton rows={4} rowHeight={28} />}

        {q.isError && (
          <div style={{ padding: 12 }}>
            <ErrorBox message="Activity feed unavailable." onRetry={() => q.refetch()} />
          </div>
        )}

        {q.isSuccess && events.length === 0 && (
          <div style={{ padding: 12 }}>
            <EmptyState title="No recent activity yet." />
          </div>
        )}

        {q.isSuccess &&
          events.map((e) => (
            <div
              key={e.id}
              onClick={() => {
                close();
                router.push(e.href);
              }}
              style={{
                padding: "10px 12px",
                borderBottom: "1px solid var(--line-1)",
                display: "flex",
                gap: 10,
                alignItems: "flex-start",
                cursor: "pointer",
              }}
            >
              <span
                aria-hidden
                style={{
                  width: 14,
                  textAlign: "center",
                  color: "var(--ink-2)",
                  fontSize: 12,
                  lineHeight: "16px",
                  flexShrink: 0,
                }}
              >
                {KIND_GLYPH[e.kind]}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--ink-0)",
                    fontWeight: 500,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={e.title}
                >
                  {truncate(e.title, 60)}
                </div>
                <div
                  className="tt-up"
                  style={{
                    fontSize: 9,
                    color: "var(--ink-3)",
                    letterSpacing: "0.08em",
                  }}
                >
                  {e.kind} · {e.summary}
                </div>
              </div>
              <span className="tab muted" style={{ fontSize: 9, flexShrink: 0 }}>
                {relativeTime(e.ts)}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
