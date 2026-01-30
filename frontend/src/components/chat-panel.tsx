"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSendMessage, useSessionMessages } from "@/hooks/use-chat";
import { Loader2 } from "lucide-react";

interface ChatPanelProps {
  paperId: string;
  sessionId: string | null;
  onSessionChange?: (sessionId: string) => void;
}

export function ChatPanel({
  paperId,
  sessionId,
  onSessionChange,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const sendMessage = useSendMessage(paperId);
  const { data: sessionData, refetch } = useSessionMessages(paperId, sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 当有新消息时自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sessionData?.messages]);

  // 当发送消息成功后，刷新消息列表
  useEffect(() => {
    if (sendMessage.isSuccess && sessionId) {
      refetch();
    }
  }, [sendMessage.isSuccess, sessionId, refetch]);

  const handleSend = () => {
    if (!message.trim() || sendMessage.isPending) return;

    sendMessage.mutate(
      {
        message: message.trim(),
        session_id: sessionId || undefined,
        language: "zh",
      },
      {
        onSuccess: (data) => {
          setMessage("");
          if (!sessionId && data.session_id) {
            onSessionChange?.(data.session_id);
          } else if (sessionId) {
            // 刷新消息列表
            refetch();
          }
        },
      }
    );
  };

  const messages = sessionData?.messages || [];

  return (
    <div className="flex flex-col h-[600px] border rounded-lg bg-background">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            开始对话吧！输入你的问题...
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {sendMessage.isPending && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg p-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">AI 正在思考...</p>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="border-t p-4 bg-background">
        <div className="flex gap-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入你的问题..."
            disabled={sendMessage.isPending}
          />
          <Button
            onClick={handleSend}
            disabled={!message.trim() || sendMessage.isPending}
          >
            {sendMessage.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "发送"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
