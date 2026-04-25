"use client";
import { useQuery } from "@tanstack/react-query";
import { api, type AgentMessage, type DiscussionRun, type DiscussionStatus } from "@/lib/api";

const TERMINAL: DiscussionStatus[] = ["completed", "failed"];

export function useDiscussionPolling(discussionId: string | null) {
  const status = useQuery<DiscussionRun>({
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

  const messages = useQuery<AgentMessage[]>({
    queryKey: ["discussion-messages", discussionId],
    queryFn: () => api.discussionMessages(discussionId!, { limit: 500 }),
    enabled: !!discussionId,
    refetchInterval: () => {
      const s = status.data?.status;
      if (s && TERMINAL.includes(s)) return false;
      return 1500;
    },
    staleTime: 0,
  });

  return { status, messages };
}
