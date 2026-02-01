"""
Semantic Scholar API client — fetches author affiliations for papers.

Usage:
    from src.service.semantic_scholar_service import SemanticScholarClient
    client = SemanticScholarClient()
    affiliations = client.fetch_affiliations("2301.02111")
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import httpx

from src.config import Config

logger = logging.getLogger(__name__)

S2_BASE = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarClient:
    def __init__(self) -> None:
        cfg = Config.semantic_scholar
        self._api_key: Optional[str] = cfg.api_key
        self._min_interval: float = cfg.min_interval
        self._retries: int = cfg.retries
        self._last_request_time: float = 0.0

    def _wait_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def fetch_affiliations(self, arxiv_id: str) -> Optional[List[str]]:
        """
        Fetch deduplicated author affiliations for a given arXiv paper.

        Args:
            arxiv_id: The arXiv ID (e.g. "2301.02111"), without the "ArXiv:" prefix.

        Returns:
            A deduplicated list of institution names, or None if not available.
        """
        url = f"{S2_BASE}/paper/ArXiv:{arxiv_id}"
        params = {"fields": "authors.affiliations"}
        headers: dict[str, str] = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        for attempt in range(1, self._retries + 1):
            self._wait_rate_limit()
            self._last_request_time = time.monotonic()

            try:
                resp = httpx.get(url, params=params, headers=headers, timeout=15.0)

                if resp.status_code == 404:
                    logger.debug("S2 paper not found: ArXiv:%s", arxiv_id)
                    return None

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", "2"))
                    logger.warning(
                        "S2 rate limited (attempt %d/%d), sleeping %.1fs",
                        attempt, self._retries, retry_after,
                    )
                    time.sleep(retry_after)
                    continue

                resp.raise_for_status()
                data = resp.json()

                # Extract and deduplicate affiliations
                seen: set[str] = set()
                affiliations: list[str] = []
                for author in data.get("authors", []):
                    for aff in author.get("affiliations", []) or []:
                        name = aff.strip() if isinstance(aff, str) else ""
                        if name and name not in seen:
                            seen.add(name)
                            affiliations.append(name)

                return affiliations if affiliations else None

            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "S2 HTTP error %d for ArXiv:%s (attempt %d/%d)",
                    exc.response.status_code, arxiv_id, attempt, self._retries,
                )
                if attempt < self._retries:
                    time.sleep(2 ** attempt)
            except httpx.RequestError as exc:
                logger.warning(
                    "S2 request error for ArXiv:%s (attempt %d/%d): %s",
                    arxiv_id, attempt, self._retries, exc,
                )
                if attempt < self._retries:
                    time.sleep(2 ** attempt)

        logger.error("S2 fetch failed after %d attempts for ArXiv:%s", self._retries, arxiv_id)
        return None
