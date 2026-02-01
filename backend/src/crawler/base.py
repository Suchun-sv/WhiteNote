"""
Base class for all paper crawlers.

To add a new feed source:
1. Create a subclass of BaseCrawler
2. Implement fetch() -> List[Paper]
3. Register it in registry.py
4. Add a feed entry in settings.yaml
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.model.paper import Paper


class BaseCrawler(ABC):
    """
    Abstract base class for paper crawlers.

    Each crawler knows how to fetch papers from a specific source
    (arXiv, OpenReview, Semantic Scholar, CSV import, etc.).
    The only contract: return a list of Paper objects.
    """

    def __init__(self, params: Dict[str, Any] | None = None):
        self.params = params or {}

    @abstractmethod
    def fetch(self) -> List[Paper]:
        """
        Fetch papers from the source.

        Returns a list of Paper objects. The caller is responsible
        for setting paper.feed before inserting into the database.
        """
        ...
