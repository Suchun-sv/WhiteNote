"""
Semantic Scholar bulk crawler (replaces legacy DBLP crawler).

Fetches main-conference papers by venue/year from Semantic Scholar bulk search,
then uses batch details to retrieve abstracts and links.

Expected params in settings.yaml:
  feeds:
    - id: cvpr-2025
      crawler: dblp
      params:
        venue: "CVPR"          # main conference venue name
        year: "2025"
        limit: null
        min_interval: 1.0
        batch_size: 500
        include_workshops: false

Legacy params:
  query: "conf/cvpr/2025" (will be parsed to venue/year where possible)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
import time

import requests

from src.crawler.base import BaseCrawler
from src.model.paper import Paper


S2_BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"

# Rate limiting settings
MAX_RETRY_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 60


class DblpCrawler(BaseCrawler):
    def __init__(self, params: Dict[str, Any] | None = None):
        super().__init__(params)
        self.query: str = self.params.get("query", "")
        self.venue: Optional[str] = self.params.get("venue")
        self.year: Optional[str] = self.params.get("year")
        raw_limit = self.params.get("limit")
        self.limit: Optional[int] = int(raw_limit) if raw_limit is not None else None
        self.min_interval: float = float(self.params.get("min_interval", 1.0))
        self.batch_size: int = int(self.params.get("batch_size", 500))
        self.include_workshops: bool = bool(self.params.get("include_workshops", False))

        if not self.venue or not self.year:
            derived_venue, derived_year = _derive_venue_year(self.query)
            if not self.venue and derived_venue:
                self.venue = derived_venue
            if not self.year and derived_year:
                self.year = derived_year

    def fetch(self) -> List[Paper]:
        import logging
        logger = logging.getLogger(__name__)
        if not self.venue:
            raise ValueError("Missing venue for Semantic Scholar bulk search")
        if not self.year:
            raise ValueError("Missing year for Semantic Scholar bulk search")

        logger.info(
            "S2 bulk crawl start: venue=%s year=%s query=%s include_workshops=%s limit=%s",
            self.venue,
            self.year,
            self.query or "",
            self.include_workshops,
            self.limit,
        )

        bulk_fields = "paperId,title,year,venue,publicationVenue,url"
        records = list(
            iter_s2_bulk_papers(
                venue=self.venue,
                year=str(self.year),
                query=self.query,
                fields=bulk_fields,
                min_interval=self.min_interval,
                limit=self.limit,
            )
        )
        logger.info("S2 bulk fetched: %s", len(records))

        main_records = [
            r
            for r in records
            if _is_main_conference(
                r,
                venue=self.venue,
                include_workshops=self.include_workshops,
            )
        ]
        logger.info("S2 bulk filtered (main conference): %s", len(main_records))

        paper_ids = [r.get("paperId") for r in main_records if r.get("paperId")]
        if not paper_ids:
            logger.warning("S2 bulk yielded no paperIds after filtering.")
            return []

        batch_fields = (
            "title,abstract,url,openAccessPdf,externalIds,authors,"
            "venue,publicationVenue,year"
        )
        details = fetch_s2_batch_details(
            paper_ids,
            fields=batch_fields,
            batch_size=self.batch_size,
            min_interval=self.min_interval,
        )
        logger.info("S2 batch details fetched: %s", len(details))

        return [self._to_paper(d) for d in details]

    def _to_paper(self, record: Dict[str, Any]) -> Paper:
        pdf_url = _extract_pdf_url(record)
        authors = _normalize_s2_authors(record.get("authors"))
        venue = record.get("venue") or ""
        keywords = [venue] if venue else []

        return Paper(
            id=record.get("paperId", "") or record.get("url", ""),
            title=record.get("title", "") or "",
            abstract=record.get("abstract", "") or "",
            authors=authors,
            keywords=keywords,
            pdf_url=pdf_url,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )


def _sleep_with_min_interval(last_ts: float | None, min_interval: float) -> float:
    now = time.time()
    if last_ts is None:
        return now
    elapsed = now - last_ts
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.time()


def _derive_venue_year(query: str) -> Tuple[Optional[str], Optional[str]]:
    if not query or not query.startswith("conf/"):
        return None, None
    parts = query.split("/")
    if len(parts) < 3:
        return None, None
    conf = parts[1].strip().lower()
    year = parts[2].strip()
    conf_map = {
        "cvpr": "CVPR",
        "iccv": "ICCV",
        "icml": "ICML",
        "iclr": "ICLR",
        "nips": "NeurIPS",
        "neurips": "NeurIPS",
        "eccv": "ECCV",
        "vldb": "VLDB",
        "sigmod": "SIGMOD",
    }
    return conf_map.get(conf), year


def _normalize_s2_authors(authors: Any) -> List[str]:
    if not isinstance(authors, list):
        return []
    out: List[str] = []
    for a in authors:
        if isinstance(a, dict):
            name = a.get("name")
            if name:
                out.append(str(name))
    return out


def _extract_pdf_url(record: Dict[str, Any]) -> Optional[str]:
    open_pdf = record.get("openAccessPdf") or {}
    if isinstance(open_pdf, dict):
        url = open_pdf.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    ext = record.get("externalIds") or {}
    if isinstance(ext, dict):
        arxiv_id = ext.get("ArXiv")
        if isinstance(arxiv_id, str) and arxiv_id.strip():
            return f"https://arxiv.org/pdf/{arxiv_id.strip()}.pdf"
    return None


def _is_main_conference(
    record: Dict[str, Any],
    venue: str,
    include_workshops: bool,
) -> bool:
    pub = record.get("publicationVenue") or {}
    venue_name = (record.get("venue") or "").strip()
    pub_name = ""
    pub_alt: List[str] = []
    if isinstance(pub, dict):
        pub_name = str(pub.get("name") or "").strip()
        alt = pub.get("alternate_names") or []
        if isinstance(alt, list):
            pub_alt = [str(a).strip() for a in alt]
    hay = " ".join([venue_name, pub_name] + pub_alt).lower()
    if not include_workshops and "workshop" in hay:
        return False
    venue_l = venue.lower()
    full_name_map = {
        "cvpr": "computer vision and pattern recognition",
        "iccv": "international conference on computer vision",
        "eccv": "european conference on computer vision",
        "icml": "international conference on machine learning",
        "iclr": "international conference on learning representations",
        "neurips": "neural information processing systems",
        "vldb": "very large data bases",
        "sigmod": "sigmod",
    }
    if venue_l in hay:
        return True
    full_name = full_name_map.get(venue_l)
    if full_name and full_name in hay:
        return True
    return False


def iter_s2_bulk_papers(
    venue: str,
    year: str,
    query: str,
    fields: str,
    min_interval: float,
    limit: Optional[int] = None,
) -> Iterable[Dict[str, Any]]:
    token: Optional[str] = None
    last_ts: float | None = None
    fetched = 0

    while True:
        last_ts = _sleep_with_min_interval(last_ts, min_interval)
        params: Dict[str, str] = {"venue": venue, "year": year, "fields": fields, "limit": "1000"}
        if query:
            params["query"] = query
        if token:
            params["token"] = token

        retries = 0
        while True:
            resp = requests.get(S2_BULK_URL, params=params, timeout=30)
            if resp.status_code == 429:
                retries += 1
                if retries > MAX_RETRY_ATTEMPTS:
                    raise RuntimeError("Semantic Scholar rate limit exceeded")
                wait_s = min(BASE_BACKOFF_SECONDS * (2 ** (retries - 1)), MAX_BACKOFF_SECONDS)
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
            payload = resp.json()
            break

        data = payload.get("data") or []
        if not isinstance(data, list) or not data:
            break
        for item in data:
            yield item
            fetched += 1
            if limit is not None and fetched >= limit:
                return
        token = payload.get("token")
        if not token:
            break


def fetch_s2_batch_details(
    paper_ids: List[str],
    fields: str,
    batch_size: int,
    min_interval: float,
) -> List[Dict[str, Any]]:
    last_ts: float | None = None
    out: List[Dict[str, Any]] = []

    for i in range(0, len(paper_ids), batch_size):
        batch = paper_ids[i : i + batch_size]
        last_ts = _sleep_with_min_interval(last_ts, min_interval)
        retries = 0
        while True:
            resp = requests.post(
                S2_BATCH_URL,
                params={"fields": fields},
                json={"ids": batch},
                timeout=30,
            )
            if resp.status_code == 429:
                retries += 1
                if retries > MAX_RETRY_ATTEMPTS:
                    raise RuntimeError("Semantic Scholar rate limit exceeded")
                wait_s = min(BASE_BACKOFF_SECONDS * (2 ** (retries - 1)), MAX_BACKOFF_SECONDS)
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                out.extend(payload)
            break

    return out
