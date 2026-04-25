"use client";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  wsUrl,
  type AgentMessage,
  type Claim,
  type DiscussionRun,
  type DiscussionStatus,
} from "@/lib/api";

// The WS phase channel can carry "criticizing" which is not in DiscussionStatus.
// We narrow it for state but expose only DiscussionStatus on the public shape so
// DebateRoom can keep using the existing status enum.
type WsPhase =
  | "researching"
  | "planning"
  | "debating"
  | "criticizing"
  | "synthesizing"
  | "completed"
  | "failed";

type AgentRtState = "thinking" | "queued" | "done" | "error";

type WsEvent =
  | { event: "phase"; phase: WsPhase; ts: string }
  | { event: "status"; agent_id: string; state: AgentRtState; extra: Record<string, unknown>; ts: string }
  | { event: "post"; agent_message: AgentMessage; ts: string }
  | { event: "claim"; claim: Claim; ts: string };

export type StreamMode = "ws" | "polling";

export type DiscussionStream = {
  mode: StreamMode;
  status: DiscussionStatus | null;
  phase: DiscussionStatus | null;
  messages: AgentMessage[];
  claims: Claim[];
  agentStatuses: Record<string, { state: string; extra: Record<string, unknown> }>;
  errorDetail: string | null;
  lastEventAt: number | null;
};

const TERMINAL: DiscussionStatus[] = ["completed", "failed"];
const OPEN_TIMEOUT_MS = 2000;
const SHUTDOWN_CODE = 4000;

// "criticizing" is a debate-loop sub-phase; UI groups it under debating.
function phaseToStatus(p: WsPhase): DiscussionStatus {
  if (p === "criticizing") return "debating";
  return p;
}

type WsState = {
  phase: DiscussionStatus | null;
  messages: AgentMessage[];
  claims: Claim[];
  agentStatuses: Record<string, { state: string; extra: Record<string, unknown> }>;
  errorDetail: string | null;
  lastEventAt: number | null;
};

const EMPTY_WS_STATE: WsState = {
  phase: null,
  messages: [],
  claims: [],
  agentStatuses: {},
  errorDetail: null,
  lastEventAt: null,
};

function reduce(prev: WsState, ev: WsEvent): WsState {
  const ts = Date.parse(ev.ts);
  const lastEventAt = Number.isFinite(ts) ? ts : Date.now();
  switch (ev.event) {
    case "phase": {
      const status = phaseToStatus(ev.phase);
      let errorDetail = prev.errorDetail;
      if (status === "failed" && !errorDetail) {
        // try to fish out a useful message from the most recent error status
        const errEntry = Object.values(prev.agentStatuses).find((s) => s.state === "error");
        const fromExtra = errEntry?.extra?.error;
        if (typeof fromExtra === "string") errorDetail = fromExtra;
      }
      return { ...prev, phase: status, errorDetail, lastEventAt };
    }
    case "status": {
      return {
        ...prev,
        agentStatuses: {
          ...prev.agentStatuses,
          [ev.agent_id]: { state: ev.state, extra: ev.extra },
        },
        lastEventAt,
      };
    }
    case "post": {
      // de-dup in case backend ever replays
      if (prev.messages.some((m) => m.id === ev.agent_message.id)) {
        return { ...prev, lastEventAt };
      }
      return { ...prev, messages: [...prev.messages, ev.agent_message], lastEventAt };
    }
    case "claim": {
      if (prev.claims.some((c) => c.id === ev.claim.id)) {
        return { ...prev, lastEventAt };
      }
      return { ...prev, claims: [...prev.claims, ev.claim], lastEventAt };
    }
  }
}

export function useDiscussionStream(discussionId: string | null): DiscussionStream {
  const [mode, setMode] = useState<StreamMode>("ws");
  const [wsState, setWsState] = useState<WsState>(EMPTY_WS_STATE);
  const wsRef = useRef<WebSocket | null>(null);

  // Reset everything when the discussion changes.
  useEffect(() => {
    setMode("ws");
    setWsState(EMPTY_WS_STATE);
  }, [discussionId]);

  useEffect(() => {
    if (!discussionId) return;
    if (typeof WebSocket === "undefined") {
      setMode("polling");
      return;
    }

    let opened = false;
    let cancelled = false;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl(discussionId));
    } catch {
      setMode("polling");
      return;
    }
    wsRef.current = ws;

    const openTimer = window.setTimeout(() => {
      if (!opened && !cancelled) {
        try {
          ws?.close(SHUTDOWN_CODE, "open-timeout");
        } catch {
          // ignore
        }
        setMode("polling");
      }
    }, OPEN_TIMEOUT_MS);

    ws.onopen = () => {
      opened = true;
      window.clearTimeout(openTimer);
      if (!cancelled) setMode("ws");
    };

    ws.onmessage = (e: MessageEvent<string>) => {
      if (cancelled) return;
      try {
        const parsed = JSON.parse(e.data) as WsEvent;
        setWsState((prev) => reduce(prev, parsed));
      } catch {
        // malformed frame; ignore but don't tear down
      }
    };

    ws.onerror = () => {
      if (cancelled) return;
      window.clearTimeout(openTimer);
      try {
        ws?.close(SHUTDOWN_CODE, "error");
      } catch {
        // ignore
      }
      setMode("polling");
    };

    ws.onclose = (ev: CloseEvent) => {
      window.clearTimeout(openTimer);
      if (cancelled) return;
      if (ev.code !== SHUTDOWN_CODE) {
        setMode("polling");
      }
    };

    return () => {
      cancelled = true;
      window.clearTimeout(openTimer);
      try {
        ws?.close(SHUTDOWN_CODE, "unmount");
      } catch {
        // ignore
      }
      if (wsRef.current === ws) wsRef.current = null;
    };
  }, [discussionId]);

  // Always poll the snapshot. WS is a live-append channel; for terminal /
  // historical discussions the WS opens but never emits, so polling is the
  // only path to the data. The two sources are merged in the return memo.
  const statusQ = useQuery<DiscussionRun>({
    queryKey: ["discussion", discussionId],
    queryFn: () => api.discussion(discussionId!),
    enabled: !!discussionId,
    refetchInterval: (query) => {
      const data = query.state.data as DiscussionRun | undefined;
      if (!data) return 1500;
      if (TERMINAL.includes(data.status)) return false;
      return 1500;
    },
    staleTime: 0,
  });

  const messagesQ = useQuery<AgentMessage[]>({
    queryKey: ["discussion-messages", discussionId],
    queryFn: () => api.discussionMessages(discussionId!, { limit: 500 }),
    enabled: !!discussionId,
    refetchInterval: () => {
      const s = statusQ.data?.status;
      if (s && TERMINAL.includes(s)) return false;
      return 1500;
    },
    staleTime: 0,
  });

  const finalClaimIds = statusQ.data?.final_claim_ids ?? [];
  const claimQs = useQueries({
    queries: finalClaimIds.map((id) => ({
      queryKey: ["claim", id],
      queryFn: () => api.claim(id),
      staleTime: 60_000,
    })),
  });
  const polledClaims: Claim[] = claimQs
    .map((q) => q.data)
    .filter((c): c is Claim => !!c);

  return useMemo<DiscussionStream>(() => {
    const detail = statusQ.data ?? null;
    const polledStatus = detail?.status ?? null;
    const errorDetail = wsState.errorDetail ?? detail?.error ?? null;

    // Merge WS append with the polled snapshot, dedup by id, keep insertion order.
    const seenMsgIds = new Set<string>();
    const messages: AgentMessage[] = [];
    for (const m of [...(messagesQ.data ?? []), ...wsState.messages]) {
      if (seenMsgIds.has(m.id)) continue;
      seenMsgIds.add(m.id);
      messages.push(m);
    }
    const seenClaimIds = new Set<string>();
    const claims: Claim[] = [];
    for (const c of [...polledClaims, ...wsState.claims]) {
      if (seenClaimIds.has(c.id)) continue;
      seenClaimIds.add(c.id);
      claims.push(c);
    }

    return {
      mode,
      // Prefer WS-emitted phase (more granular - includes "criticizing")
      // but fall back to polled status for past/terminal discussions.
      status: wsState.phase ?? polledStatus,
      phase: wsState.phase ?? polledStatus,
      messages,
      claims,
      agentStatuses: wsState.agentStatuses,
      errorDetail,
      lastEventAt: wsState.lastEventAt,
    };
  }, [mode, wsState, statusQ.data, messagesQ.data, polledClaims]);
}
