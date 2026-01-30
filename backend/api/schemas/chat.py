from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 如果提供，使用现有会话；否则创建新会话
    language: str = "zh"  # 回复语言


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str


class ChatSessionInfo(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str


class ChatHistoryResponse(BaseModel):
    sessions: List[ChatSessionInfo]


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    created_at: str


class SessionMessagesResponse(BaseModel):
    session_id: str
    title: Optional[str] = None
    messages: List[ChatMessage]
