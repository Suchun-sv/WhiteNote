"""
OpenReview crawler — fetches papers from OpenReview venues (ICLR, NeurIPS, etc.).

Expected params in settings.yaml:
  feeds:
    - id: iclr-2026
      crawler: openreview
      params:
        venue: "ICLR.cc/2026/Conference"
        status: "accepted"           # accepted | submitted | all
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import openreview

from src.crawler.base import BaseCrawler
from src.model.paper import Paper


class OpenReviewCrawler(BaseCrawler):
    def __init__(self, params: Dict[str, Any] | None = None):
        super().__init__(params)
        self.venue = self.params.get("venue", "")
        self.status = self.params.get("status", "accepted")

    def fetch(self) -> List[Paper]:
        client = openreview.api.OpenReviewClient(
            baseurl="https://api2.openreview.net",
        )

        # Get venue group to discover the submission invitation name
        venue_group = client.get_group(self.venue)
        submission_name = venue_group.content["submission_name"]["value"]

        if self.status == "accepted":
            # Accepted papers have their venueid set to the venue
            notes = client.get_all_notes(content={"venueid": self.venue})
        else:
            # All submissions (including under review)
            notes = client.get_all_notes(
                invitation=f"{self.venue}/-/{submission_name}",
            )

        return [self._to_paper(note) for note in notes]

    def _to_paper(self, note: openreview.api.Note) -> Paper:
        content = note.content

        # Timestamps are in milliseconds
        ts = note.cdate or note.tcdate
        published = (
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else None
        )

        pdf_value = content.get("pdf", {}).get("value", "")
        pdf_url = (
            f"https://openreview.net{pdf_value}" if pdf_value else None
        )

        return Paper(
            id=note.id,
            title=content["title"]["value"],
            abstract=content.get("abstract", {}).get("value", ""),
            authors=content.get("authors", {}).get("value", []),
            keywords=content.get("keywords", {}).get("value", []),
            pdf_url=pdf_url,
            arxiv_published=published,
        )
