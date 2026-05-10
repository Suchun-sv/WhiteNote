"""Zotero integration tools."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from src.database.paper_repository import PaperRepository
from src.mcp_server.adapters import zotero as zotero_adapter


def register(mcp: FastMCP) -> None:
    repo = PaperRepository()

    @mcp.tool()
    def list_zotero_collections() -> Dict[str, Any]:
        """List the user's Zotero collections (key + name)."""
        try:
            return {"collections": zotero_adapter.list_collections()}
        except zotero_adapter.ZoteroNotConfigured as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Zotero API error: {e}"}

    @mcp.tool()
    def save_to_zotero(
        paper_id: str,
        collection_key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        attach_pdf: bool = False,
    ) -> Dict[str, Any]:
        """Push a paper to the configured Zotero library.

        - `collection_key`: optional Zotero collection (see `list_zotero_collections`).
          Falls back to `zotero.default_collection` from config.
        - `tags`: extra tags to add (arXiv categories are included automatically).
        - `attach_pdf`: also upload the cached PDF as an attachment (slower).
        """
        paper = repo.get_paper_by_id(paper_id)
        if not paper:
            return {"error": f"paper {paper_id} not found"}
        try:
            result = zotero_adapter.save_paper(
                paper=paper,
                collection_key=collection_key,
                extra_tags=tags,
                attach_pdf=attach_pdf,
            )
        except zotero_adapter.ZoteroNotConfigured as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Zotero API error: {e}"}

        return {"ok": True, "paper_id": paper_id, **result}
