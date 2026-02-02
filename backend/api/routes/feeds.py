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
    """Extract year from feed id (e.g. iclr-2026) or openreview venue param."""
    # Try id pattern like "iclr-2026", "neurips-2025"
    m = re.search(r"-(\d{4})$", f.id)
    if m:
        return int(m.group(1))
    # OpenReview venue e.g. "ICLR.cc/2026/Conference"
    venue = (f.params or {}).get("venue", "")
    m = re.search(r"/(\d{4})/", venue)
    if m:
        return int(m.group(1))
    return None


class FeedInfo(BaseModel):
    id: str
    name: str
    crawler: str = "arxiv"
    year: Optional[int] = None


@router.get("", response_model=List[FeedInfo])
def list_feeds():
    """Return configured feeds (for add-feed selector)."""
    return [
        FeedInfo(
            id=f.id,
            name=f.name,
            crawler=f.crawler,
            year=_year_from_feed(f),
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
    return [
        FeedInfo(
            id=fid,
            name=_name_for_feed_id(fid),
        )
        for fid in feed_ids
    ]
