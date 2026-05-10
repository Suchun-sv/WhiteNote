"""Multi-turn Q&A over a single paper."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastmcp import FastMCP

from src.config import Config
from src.database.paper_repository import PaperRepository
from src.service.chat_service import ChatService


def register(mcp: FastMCP) -> None:
    repo = PaperRepository()
    chat = ChatService()

    @mcp.tool()
    def chat_with_paper(
        paper_id: str,
        question: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ask a question about a paper. Pass the returned `session_id` on
        follow-up calls to continue the same conversation."""
        paper = repo.get_paper_by_id(paper_id)
        if not paper:
            return {"error": f"paper {paper_id} not found"}

        if session_id is None:
            session = chat.create_session(
                paper_id=paper_id,
                paper_title=paper.title,
                paper_abstract=paper.abstract,
                paper_full_text=paper.full_text,
                paper_summary=paper.ai_summary,
                language=Config.language,
            )
            session_id = session.id

        answer = chat.ask(session_id, question)
        return {"session_id": session_id, "answer": answer}

    @mcp.tool()
    def list_chat_sessions(paper_id: str) -> Any:
        """List existing chat sessions for a paper."""
        sessions = chat.get_sessions_by_paper(paper_id)
        return [
            {"id": s.id, "title": s.title, "created_at": str(s.created_at)}
            for s in sessions
        ]
