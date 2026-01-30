from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_paper_repo
from api.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    SessionMessagesResponse,
    ChatSessionInfo,
    ChatMessage as ChatMessageSchema,
)
from src.database.paper_repository import PaperRepository
from src.service.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


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
        ChatSessionInfo(
            id=s.id,
            title=s.title or "新对话",
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]

    return ChatHistoryResponse(sessions=sessions_data)


@router.get("/{paper_id}/sessions/{session_id}", response_model=SessionMessagesResponse)
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
        ChatMessageSchema(
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
        )
        for msg in session.messages
        if msg.role != "system"  # 不返回 system prompt
    ]

    return SessionMessagesResponse(
        session_id=session.id,
        title=session.title,
        messages=messages,
    )
