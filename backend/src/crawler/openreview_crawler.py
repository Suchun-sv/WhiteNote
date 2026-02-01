"""
OpenReview crawler — fetches papers from OpenReview venues (ICLR, NeurIPS, etc.).

Expected params in settings.yaml:
  feeds:
    - id: iclr-2026
      crawler: openreview
      params:
        venue: "ICLR.cc/2026/Conference"
        status: "accepted"           # accepted | submitted | all

TODO: implement fetch() using the OpenReview API.
      See https://docs.openreview.net/ for API documentation.
"""

from typing import Any, Dict, List

from src.crawler.base import BaseCrawler
from src.model.paper import Paper


class OpenReviewCrawler(BaseCrawler):
    def __init__(self, params: Dict[str, Any] | None = None):
        super().__init__(params)
        self.venue = self.params.get("venue", "")
        self.status = self.params.get("status", "accepted")

    def fetch(self) -> List[Paper]:
        # TODO: implement OpenReview API integration
        # Example flow:
        #   1. Query OpenReview API for papers in self.venue
        #   2. Filter by self.status
        #   3. Convert each result to a Paper object
        #   4. Return the list
        raise NotImplementedError(
            f"OpenReviewCrawler for venue '{self.venue}' is not yet implemented. "
            "Please implement the fetch() method."
        )
