"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSendMessage, useSessionMessages } from "@/hooks/use-chat";
import { Loader2, Send } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  paperId: string;
  sessionId: string | null;
  onSessionChange?: (sessionId: string) => void;
  className?: string;
}

export function ChatPanel({
  paperId,
  sessionId,
  onSessionChange,
  className,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const sendMessage = useSendMessage(paperId);
  const { data: sessionData, refetch } = useSessionMessages(paperId, sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sessionData?.messages]);

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
            refetch();
          }
        },
      }
    );
  };

  const messages = sessionData?.messages || [];

  return (
    <div className={cn("flex flex-col h-[500px]", className)}>
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto space-y-3 pb-2">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-xs py-6">
            输入问题，开始与 AI 讨论这篇论文
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
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              )}
            >
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
        {sendMessage.isPending && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                <p className="text-xs text-muted-foreground">AI 正在思考...</p>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="border-t pt-3">
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
            className="text-sm"
          />
          <Button
            onClick={handleSend}
            disabled={!message.trim() || sendMessage.isPending}
            size="icon"
          >
            {sendMessage.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
