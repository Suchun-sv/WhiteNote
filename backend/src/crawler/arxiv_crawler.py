"""
arXiv crawler — fetches papers by keyword search.

Expected params in settings.yaml:
  feeds:
    - id: arxiv
      crawler: arxiv
      params:
        keywords: ["RAG", "agent", "vector database"]
        max_results: 100
"""

import re
from datetime import datetime
from typing import Any, Dict, List

import arxiv

from src.crawler.base import BaseCrawler
from src.model.paper import Paper


class ArxivCrawler(BaseCrawler):
    def __init__(self, params: Dict[str, Any] | None = None):
        super().__init__(params)
        self.arxiv_client = arxiv.Client(
            page_size=100,
            delay_seconds=1,
            num_retries=3,
        )

    def fetch(self) -> List[Paper]:
        keywords: List[str] = self.params.get("keywords", [])
        max_results: int = self.params.get("max_results", 100)

        all_papers: List[Paper] = []
        seen_ids: set[str] = set()

        for keyword in keywords:
            query = keyword
            if " " in keyword and not (keyword.startswith('"') and keyword.endswith('"')):
                query = f'"{keyword}"'

            search_query = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            results = self.arxiv_client.results(search_query)

            for result in results:
                paper = self._to_paper(result, keyword)
                if paper.id not in seen_ids:
                    all_papers.append(paper)
                    seen_ids.add(paper.id)

        return all_papers

    # --- internal helpers (unchanged from ArxivClient) ---

    @staticmethod
    def _normalize_arxiv_id(arxiv_id: str) -> str:
        last = arxiv_id.split("/")[-1]
        return re.sub(r"v\d+", "", last)

    @staticmethod
    def _get_pdf_url(result: arxiv.Result) -> str:
        for link in result.links:
            if "pdf" in link.href.lower():
                return link.href
        return ""

    def _to_paper(self, result: arxiv.Result, keyword: str) -> Paper:
        return Paper(
            id=self._normalize_arxiv_id(result.entry_id),
            title=result.title,
            abstract=result.summary,
            authors=[a.name for a in result.authors],
            pdf_url=self._get_pdf_url(result),
            keywords=[keyword],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            arxiv_entry_id=result.entry_id,
            arxiv_updated=result.updated,
            arxiv_published=result.published,
            arxiv_authors=[a.name for a in result.authors],
            arxiv_links=[link.href for link in result.links],
            arxiv_comment=result.comment,
            arxiv_journal_ref=result.journal_ref,
            arxiv_doi=result.doi,
            arxiv_primary_category=result.primary_category,
            arxiv_categories=result.categories,
        )
