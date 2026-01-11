# src/model/chat.py

"""
Chat 数据模型

用于论文问答的会话和消息管理
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ChatMessage(BaseModel):
    """聊天消息"""
    id: Optional[int] = None
    session_id: str
    role: str  # system | user | assistant
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    """聊天会话"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    paper_id: str
    title: Optional[str] = None  # 自动生成的标题
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    messages: List[ChatMessage] = Field(default_factory=list)

    model_config = {
        "str_strip_whitespace": True,
    }

