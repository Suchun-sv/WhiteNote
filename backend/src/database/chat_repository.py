# src/database/chat_repository.py

"""
Chat Repository - 管理聊天会话和消息

功能：
- 创建/获取/删除会话
- 添加消息
- 自动生成会话标题
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, desc

from src.model.chat import ChatSession, ChatMessage
from src.database.db.session import SessionLocal
from src.database.db.models import ChatSessionRow, ChatMessageRow


class ChatRepository:
    """聊天数据仓库"""

    # =====================================================
    # Session CRUD
    # =====================================================

    def create_session(
        self,
        paper_id: str,
        system_prompt: str,
        title: Optional[str] = None,
    ) -> ChatSession:
        """
        创建新的聊天会话
        
        Args:
            paper_id: 关联的论文 ID
            system_prompt: 系统提示（包含论文内容）
            title: 会话标题（可选，后续会自动生成）
        
        Returns:
            新创建的会话
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with SessionLocal() as db:
            # 创建会话
            session_row = ChatSessionRow(
                id=session_id,
                paper_id=paper_id,
                title=title,
                created_at=now,
                updated_at=now,
            )
            db.add(session_row)
            
            # 添加 system 消息
            system_msg = ChatMessageRow(
                session_id=session_id,
                role="system",
                content=system_prompt,
                created_at=now,
            )
            db.add(system_msg)
            
            db.commit()
            db.refresh(session_row)
            
            return self._row_to_session(session_row)

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话（包含所有消息）"""
        with SessionLocal() as db:
            row = db.get(ChatSessionRow, session_id)
            if not row:
                return None
            return self._row_to_session(row)

    def get_sessions_by_paper(self, paper_id: str) -> List[ChatSession]:
        """获取论文的所有会话（不包含消息内容，用于列表显示）"""
        with SessionLocal() as db:
            rows = db.execute(
                select(ChatSessionRow)
                .where(ChatSessionRow.paper_id == paper_id)
                .order_by(desc(ChatSessionRow.updated_at))
            ).scalars().all()
            
            return [self._row_to_session(row, include_messages=False) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        """删除会话（级联删除所有消息）"""
        with SessionLocal() as db:
            row = db.get(ChatSessionRow, session_id)
            if not row:
                return False
            
            db.delete(row)
            db.commit()
            return True

    def update_session_title(self, session_id: str, title: str) -> None:
        """更新会话标题"""
        with SessionLocal() as db:
            row = db.get(ChatSessionRow, session_id)
            if not row:
                return
            
            row.title = title
            row.updated_at = datetime.utcnow()
            db.commit()

    # =====================================================
    # Message CRUD
    # =====================================================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Optional[ChatMessage]:
        """
        添加消息到会话
        
        Args:
            session_id: 会话 ID
            role: 消息角色 (user | assistant)
            content: 消息内容
        
        Returns:
            新添加的消息，如果会话不存在返回 None
        """
        with SessionLocal() as db:
            # 检查会话是否存在
            session_row = db.get(ChatSessionRow, session_id)
            if not session_row:
                return None
            
            # 添加消息
            now = datetime.utcnow()
            msg_row = ChatMessageRow(
                session_id=session_id,
                role=role,
                content=content,
                created_at=now,
            )
            db.add(msg_row)
            
            # 更新会话时间
            session_row.updated_at = now
            
            db.commit()
            db.refresh(msg_row)
            
            return ChatMessage(
                id=msg_row.id,
                session_id=msg_row.session_id,
                role=msg_row.role,
                content=msg_row.content,
                created_at=msg_row.created_at,
            )

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """获取会话的所有消息"""
        with SessionLocal() as db:
            rows = db.execute(
                select(ChatMessageRow)
                .where(ChatMessageRow.session_id == session_id)
                .order_by(ChatMessageRow.created_at)
            ).scalars().all()
            
            return [
                ChatMessage(
                    id=row.id,
                    session_id=row.session_id,
                    role=row.role,
                    content=row.content,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    # =====================================================
    # Title Generation
    # =====================================================

    def auto_generate_title(self, session_id: str) -> Optional[str]:
        """
        根据第一个用户问题自动生成标题
        
        Returns:
            生成的标题，如果没有用户消息返回 None
        """
        with SessionLocal() as db:
            # 获取第一个用户消息
            first_user_msg = db.execute(
                select(ChatMessageRow)
                .where(ChatMessageRow.session_id == session_id)
                .where(ChatMessageRow.role == "user")
                .order_by(ChatMessageRow.created_at)
                .limit(1)
            ).scalar_one_or_none()
            
            if not first_user_msg:
                return None
            
            # 截取前 30 个字符作为标题
            title = first_user_msg.content[:30]
            if len(first_user_msg.content) > 30:
                title += "..."
            
            # 更新标题
            session_row = db.get(ChatSessionRow, session_id)
            if session_row:
                session_row.title = title
                session_row.updated_at = datetime.utcnow()
                db.commit()
            
            return title

    # =====================================================
    # Helper Methods
    # =====================================================

    def _row_to_session(
        self,
        row: ChatSessionRow,
        include_messages: bool = True,
    ) -> ChatSession:
        """将数据库行转换为 Pydantic 模型"""
        messages = []
        if include_messages and row.messages:
            messages = [
                ChatMessage(
                    id=msg.id,
                    session_id=msg.session_id,
                    role=msg.role,
                    content=msg.content,
                    created_at=msg.created_at,
                )
                for msg in sorted(row.messages, key=lambda m: m.created_at)
            ]
        
        return ChatSession(
            id=row.id,
            paper_id=row.paper_id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
            messages=messages,
        )

    def get_session_count(self, paper_id: str) -> int:
        """获取论文的会话数量"""
        with SessionLocal() as db:
            from sqlalchemy import func
            count = db.execute(
                select(func.count(ChatSessionRow.id))
                .where(ChatSessionRow.paper_id == paper_id)
            ).scalar()
            return count or 0

