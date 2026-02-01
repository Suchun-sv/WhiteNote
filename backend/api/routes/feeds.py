from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import re

from src.config import Config
from src.config.config import FeedConfig

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
    """Return configured feeds for the frontend tabs (with crawler and year for add-feed selector)."""
    return [
        FeedInfo(
            id=f.id,
            name=f.name,
            crawler=f.crawler,
            year=_year_from_feed(f),
        )
        for f in Config.feeds
    ]
