from sqlalchemy import (
    Column,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime


Base = declarative_base()


class PaperRow(Base):
    __tablename__ = "papers"

    id = Column(Text, primary_key=True)
    paper = Column(JSONB, nullable=False)

    title = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    arxiv_entry_id = Column(Text)
    arxiv_published = Column(DateTime)
    arxiv_updated = Column(DateTime)


class PaperUserMeta(Base):
    __tablename__ = "paper_user_meta"

    user_id = Column(Text, primary_key=True)
    paper_id = Column(Text, primary_key=True)

    liked = Column(Boolean, default=False)
    later = Column(Boolean, default=False)
    related = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow)


class FolderRow(Base):
    """Persistent folder — allows empty folders to survive."""
    __tablename__ = "folders"

    name = Column(Text, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSessionRow(Base):
    """聊天会话"""
    __tablename__ = "chat_sessions"

    id = Column(Text, primary_key=True)  # UUID
    paper_id = Column(Text, ForeignKey("papers.id"), nullable=False, index=True)
    title = Column(Text, nullable=True)  # 自动生成的标题
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    messages = relationship("ChatMessageRow", back_populates="session", cascade="all, delete-orphan")


class ChatMessageRow(Base):
    """聊天消息"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Text, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(Text, nullable=False)  # system | user | assistant
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    session = relationship("ChatSessionRow", back_populates="messages")