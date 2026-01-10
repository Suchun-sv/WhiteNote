from sqlalchemy import (
    Column,
    Text,
    DateTime,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
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