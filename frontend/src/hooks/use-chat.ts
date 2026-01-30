import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  sendChatMessage,
  getChatHistory,
  getSessionMessages,
  type ChatMessageRequest,
} from "@/lib/api";

export function useChatHistory(paperId: string) {
  return useQuery({
    queryKey: ["chat", "history", paperId],
    queryFn: () => getChatHistory(paperId),
  });
}

export function useSessionMessages(paperId: string, sessionId: string | null) {
  return useQuery({
    queryKey: ["chat", "session", paperId, sessionId],
    queryFn: () => {
      if (!sessionId) throw new Error("Session ID required");
      return getSessionMessages(paperId, sessionId);
    },
    enabled: !!sessionId,
  });
}

export function useSendMessage(paperId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: ChatMessageRequest) =>
      sendChatMessage(paperId, body),
    onSuccess: (data, variables) => {
      // 刷新会话历史
      queryClient.invalidateQueries({
        queryKey: ["chat", "history", paperId],
      });
      // 刷新当前会话的消息
      if (data.session_id) {
        queryClient.invalidateQueries({
          queryKey: ["chat", "session", paperId, data.session_id],
        });
      }
    },
  });
}
