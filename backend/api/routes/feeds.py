from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import re

from api.deps import get_paper_repo
from src.config import Config
from src.config.config import FeedConfig
from src.database.paper_repository import PaperRepository

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


def _year_from_feed(f: FeedConfig) -> Optional[int]:
    """Extract year from feed id (e.g. iclr-2026), openreview venue param, or params.year."""
    # Try id pattern like "iclr-2026", "neurips-2025"
    m = re.search(r"-(\d{4})$", f.id)
    if m:
        return int(m.group(1))
    # OpenReview venue e.g. "ICLR.cc/2026/Conference"
    venue = (f.params or {}).get("venue", "")
    m = re.search(r"/(\d{4})/", venue)
    if m:
        return int(m.group(1))
    # DBLP crawler params.year (e.g. "2025")
    year_param = (f.params or {}).get("year")
    if year_param:
        try:
            return int(year_param)
        except (ValueError, TypeError):
            pass
    return None


class FeedInfo(BaseModel):
    id: str
    name: str
    crawler: str = "arxiv"
    year: Optional[int] = None
    supports_year_filter: bool = False


def _supports_year_filter(f: FeedConfig) -> bool:
    """Check if the crawler for this feed supports year-based filtering.
    
    - arxiv: No year filtering support (searches by keyword only)
    - dblp (Semantic Scholar bulk): Supports year filtering via params.year
    - openreview: No year filtering (venue determines year)
    """
    return f.crawler == "dblp"


@router.get("", response_model=List[FeedInfo])
def list_feeds():
    """Return configured feeds (for add-feed selector)."""
    return [
        FeedInfo(
            id=f.id,
            name=f.name,
            crawler=f.crawler,
            year=_year_from_feed(f),
            supports_year_filter=_supports_year_filter(f),
        )
        for f in Config.feeds
    ]


def _name_for_feed_id(feed_id: str) -> str:
    """Display name from Config if present, else feed_id."""
    for f in Config.feeds:
        if f.id == feed_id:
            return f.name
    return feed_id


@router.get("/from-db", response_model=List[FeedInfo])
def list_feeds_from_db(repo: PaperRepository = Depends(get_paper_repo)):
    """Return distinct feeds from papers table (for tabs). Name from Config when available."""
    feed_ids = repo.get_distinct_feed_ids()
    if not feed_ids and Config.feeds:
        feed_ids = [Config.feeds[0].id]
    
    # Build lookup from config
    config_feeds_by_id = {f.id: f for f in Config.feeds}
    
    result = []
    for fid in feed_ids:
        config_feed = config_feeds_by_id.get(fid)
        result.append(FeedInfo(
            id=fid,
            name=_name_for_feed_id(fid),
            crawler=config_feed.crawler if config_feed else "unknown",
            year=_year_from_feed(config_feed) if config_feed else None,
            supports_year_filter=_supports_year_filter(config_feed) if config_feed else False,
        ))
    return result
