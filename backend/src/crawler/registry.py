"""
Crawler registry — maps crawler type names to their classes.

To register a new crawler:
1. Import the class
2. Add an entry to CRAWLER_REGISTRY
"""

from typing import Dict, Type

from src.crawler.base import BaseCrawler
from src.crawler.arxiv_crawler import ArxivCrawler
from src.crawler.dblp_crawler import DblpCrawler
from src.crawler.openreview_crawler import OpenReviewCrawler

CRAWLER_REGISTRY: Dict[str, Type[BaseCrawler]] = {
    "arxiv": ArxivCrawler,
    "dblp": DblpCrawler,
    "openreview": OpenReviewCrawler,
}
