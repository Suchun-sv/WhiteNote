# WhiteNote 开发进度

## 当前状态总结

### ✅ Milestone 0 — 开发环境 & 项目骨架 (已完成)

- [x] FastAPI 项目骨架 (`backend/main.py`)
- [x] CORS 中间件配置（开发环境允许所有来源）
- [x] `GET /api/health` 健康检查端点
- [x] Next.js 项目初始化（App Router + TailwindCSS）
- [x] shadcn/ui 组件库配置
- [x] 前后端通信验证（已解决 CORS 和错误处理问题）

### ✅ Milestone 1 — 论文列表 API + 前端卡片流 (已完成)

- [x] 后端：`GET /api/papers?page=&size=&keyword=`（分页 + 筛选）
- [x] 后端：`GET /api/papers/{id}`（论文详情）
- [x] 后端：Pydantic response schema（`PaperListResponse`、`PaperDetail`）
- [x] 后端：`api/deps.py`（数据库 session 依赖注入）
- [x] 前端：TanStack Query 集成
- [x] 前端：`<PaperCard>` 组件（标题 + 作者 + AI 摘要）
- [x] 前端：首页论文列表 + 分页按钮

### ✅ Milestone 2 — 收藏 & 收藏夹管理 (已完成)

- [x] 后端：`POST /api/papers/{id}/favorite`（收藏）
- [x] 后端：`DELETE /api/papers/{id}/favorite`（取消收藏）
- [x] 后端：`POST /api/papers/{id}/dislike`（标记不感兴趣）
- [x] 后端：`GET /api/collections`（收藏夹列表）
- [x] 后端：`POST /api/collections`（创建收藏夹）
- [x] 后端：`PUT /api/collections/{id}`（重命名）
- [x] 后端：`DELETE /api/collections/{id}`（删除）
- [x] 前端：论文卡片上的收藏按钮（TanStack Query 乐观更新）
- [x] 前端：收藏夹列表页 `/collections`
- [x] 前端：收藏夹详情页 `/collections/[folderId]`

### ✅ Milestone 3 — AI 对话（非流式）(已完成)

**目标：** 能在论文详情页跟 AI 进行问答。先做非流式，降低复杂度。

**已完成：**
- [x] 后端：`ChatService` 已存在（`backend/src/service/chat_service.py`）
- [x] 后端：`ask()` 方法支持非流式对话

**已完成：**
- [x] 后端：创建 `api/routes/chat.py` 路由文件
- [x] 后端：`POST /api/chat/{paperId}`（发送消息 + 返回 AI 完整回复）
- [x] 后端：`GET /api/chat/{paperId}/history`（获取对话历史）
- [x] 后端：`GET /api/chat/{paperId}/sessions/{sessionId}`（获取会话消息）
- [x] 前端：创建论文详情页 `/paper/[id]`（展示论文元信息）
- [x] 前端：聊天面板组件（消息气泡 + 输入框）
- [x] 前端：调用 chat API 并展示 AI 回复
- [x] 前端：在 PaperCard 上添加"查看详情"按钮

---

## 下一步：完成 Milestone 3

### 详细实现步骤

#### 步骤 1: 创建后端 Chat API 路由

创建 `backend/api/routes/chat.py`：

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.deps import get_paper_repo
from src.database.paper_repository import PaperRepository
from src.service.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Request/Response schemas
class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 如果提供，使用现有会话；否则创建新会话
    language: str = "zh"  # 回复语言

class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str

class ChatHistoryResponse(BaseModel):
    sessions: list[dict]  # 会话列表，每个包含 id, title, created_at

@router.post("/{paper_id}", response_model=ChatMessageResponse)
def send_message(
    paper_id: str,
    body: ChatMessageRequest,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """发送消息并获取 AI 回复"""
    # 1. 获取论文信息
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 2. 初始化 ChatService
    chat_service = ChatService()
    
    # 3. 获取或创建会话
    if body.session_id:
        session = chat_service.get_session(body.session_id)
        if not session or session.paper_id != paper_id:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = body.session_id
    else:
        # 创建新会话
        session = chat_service.create_session(
            paper_id=paper_id,
            paper_title=paper.title,
            paper_abstract=paper.abstract or "",
            paper_full_text=paper.full_text,
            paper_summary=paper.ai_summary,
            language=body.language,
        )
        session_id = session.id
    
    # 4. 发送消息并获取回复
    reply = chat_service.ask(session_id, body.message)
    if not reply:
        raise HTTPException(status_code=500, detail="Failed to get AI reply")
    
    return ChatMessageResponse(session_id=session_id, reply=reply)

@router.get("/{paper_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(
    paper_id: str,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """获取论文的所有会话历史"""
    # 验证论文存在
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 获取所有会话
    chat_service = ChatService()
    sessions = chat_service.get_sessions_by_paper(paper_id)
    
    # 转换为字典格式
    sessions_data = [
        {
            "id": s.id,
            "title": s.title or "新对话",
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]
    
    return ChatHistoryResponse(sessions=sessions_data)

@router.get("/{paper_id}/sessions/{session_id}")
def get_session_messages(
    paper_id: str,
    session_id: str,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """获取特定会话的所有消息"""
    # 验证论文存在
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 获取会话
    chat_service = ChatService()
    session = chat_service.get_session(session_id)
    if not session or session.paper_id != paper_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 返回消息列表（排除 system 消息）
    messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in session.messages
        if msg.role != "system"  # 不返回 system prompt
    ]
    
    return {
        "session_id": session.id,
        "title": session.title,
        "messages": messages,
    }
```

然后在 `backend/main.py` 中注册路由：

```python
from api.routes.chat import router as chat_router

app.include_router(chat_router)
```

#### 步骤 2: 创建前端 API 函数

在 `frontend/src/lib/api.ts` 中添加：

```typescript
// Chat API
export interface ChatMessageRequest {
  message: string;
  session_id?: string;
  language?: string;
}

export interface ChatMessageResponse {
  session_id: string;
  reply: string;
}

export interface ChatHistoryResponse {
  sessions: Array<{
    id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
  }>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface SessionMessagesResponse {
  session_id: string;
  title: string | null;
  messages: ChatMessage[];
}

export function sendChatMessage(
  paperId: string,
  body: ChatMessageRequest
): Promise<ChatMessageResponse> {
  return apiPost<ChatMessageResponse>(`/api/chat/${paperId}`, body);
}

export function getChatHistory(paperId: string): Promise<ChatHistoryResponse> {
  return apiFetch<ChatHistoryResponse>(`/api/chat/${paperId}/history`);
}

export function getSessionMessages(
  paperId: string,
  sessionId: string
): Promise<SessionMessagesResponse> {
  return apiFetch<SessionMessagesResponse>(
    `/api/chat/${paperId}/sessions/${sessionId}`
  );
}
```

#### 步骤 3: 创建前端 Hooks

创建 `frontend/src/hooks/use-chat.ts`：

```typescript
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
```

#### 步骤 4: 创建聊天面板组件

创建 `frontend/src/components/chat-panel.tsx`：

```typescript
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSendMessage, useSessionMessages } from "@/hooks/use-chat";

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
  const { data: sessionData } = useSessionMessages(paperId, sessionId);

  const handleSend = () => {
    if (!message.trim()) return;

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
          }
        },
      }
    );
  };

  const messages = sessionData?.messages || [];

  return (
    <div className="flex flex-col h-[600px] border rounded-lg">
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
              <p className="text-sm text-muted-foreground">AI 正在思考...</p>
            </div>
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div className="border-t p-4">
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
            发送
          </Button>
        </div>
      </div>
    </div>
  );
}
```

#### 步骤 5: 创建论文详情页

创建 `frontend/src/app/paper/[id]/page.tsx`：

```typescript
"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchPaperById } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { ChatPanel } from "@/components/chat-panel";
import { useState } from "react";

interface PaperPageProps {
  params: Promise<{ id: string }>;
}

export default function PaperPage({ params }: PaperPageProps) {
  const { id } = use(params);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const { data: paper, isLoading } = useQuery({
    queryKey: ["paper", id],
    queryFn: () => fetchPaperById(id),
  });

  if (isLoading) {
    return <div>加载中...</div>;
  }

  if (!paper) {
    return <div>论文不存在</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {/* 论文信息 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-4">
            {paper.ai_title || paper.title}
          </h1>
          <div className="text-sm text-muted-foreground mb-4">
            <p>作者: {paper.authors.join(", ")}</p>
            {paper.arxiv_published && (
              <p>发布时间: {new Date(paper.arxiv_published).toLocaleDateString()}</p>
            )}
          </div>
          {paper.pdf_url && (
            <a
              href={paper.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              查看 PDF
            </a>
          )}
        </div>

        {/* 摘要 */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-2">摘要</h2>
          <p className="text-muted-foreground whitespace-pre-wrap">
            {paper.ai_abstract || paper.abstract}
          </p>
        </div>

        {/* AI 对话 */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">AI 对话</h2>
          <ChatPanel
            paperId={id}
            sessionId={sessionId}
            onSessionChange={setSessionId}
          />
        </div>
      </main>
    </div>
  );
}
```

#### 步骤 6: 更新 PaperCard 组件

在 `frontend/src/components/paper-card.tsx` 中添加"查看详情"按钮：

```typescript
import Link from "next/link";
// ... 其他 imports

export function PaperCard({ paper }: PaperCardProps) {
  // ... 现有代码

  return (
    <Card className="transition-shadow hover:shadow-md">
      {/* ... 现有内容 */}
      <CardContent className="space-y-3">
        {/* ... 现有内容 */}
        <Link href={`/paper/${paper.id}`}>
          <Button variant="outline" size="sm" className="w-full">
            查看详情
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
```

---

## 验收标准

完成 Milestone 3 后应该能够：

- [ ] 点击论文卡片上的"详情"按钮，跳转到论文详情页
- [ ] 在详情页能看到论文的完整信息（标题、作者、摘要等）
- [ ] 在详情页能看到聊天面板
- [ ] 输入问题后，能收到 AI 文字回复
- [ ] 刷新页面后对话历史保留（需要实现会话持久化）

---

## 后续 Milestone 预览

- **Milestone 4** — AI 流式对话 + LaTeX 渲染
- **Milestone 5** — Alembic 迁移 + Celery 替换 RQ
- **Milestone 6** — 无限滚动 + 语义搜索
- **Milestone 7** — Docker 全容器化 + MinIO
- **Milestone 8** — JWT 认证 + 多用户
- **Milestone 9** — 增强功能（推荐系统、PWA 等）
