"""
DBLP crawler — fetches papers by venue/year from the dblp search API
and then queries per-paper record XML for details.

Expected params in settings.yaml:
  feeds:
    - id: icml-2025
      crawler: dblp
      params:
        query: "conf/icml/2025"
        year: "2025"
        venue_contains: "ICML"
        limit: 200
        per_page: 100
        min_interval: 1.0
        max_pages: null
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
import time
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, quote, urlparse

import requests

from src.crawler.base import BaseCrawler
from src.model.paper import Paper


DBLP_SEARCH_URLS = [
    "https://dblp.org/search/publ/api",
    "https://dblp.uni-trier.de/search/publ/api",
    "https://dblp.dagstuhl.de/search/publ/api",
]

DBLP_REC_URLS = [
    "https://dblp.org/rec",
    "https://dblp.uni-trier.de/rec",
    "https://dblp.dagstuhl.de/rec",
]


class DblpCrawler(BaseCrawler):
    def __init__(self, params: Dict[str, Any] | None = None):
        super().__init__(params)
        self.query: str = self.params.get("query", "")
        self.year: Optional[str] = self.params.get("year")
        self.venue_contains: str = self.params.get("venue_contains", "")
        self.limit: int = int(self.params.get("limit", 100))
        self.per_page: int = int(self.params.get("per_page", 100))
        self.min_interval: float = float(self.params.get("min_interval", 1.0))
        self.max_pages: Optional[int] = self.params.get("max_pages")
        raw_types = self.params.get("type_includes", "conference and workshop papers")
        if isinstance(raw_types, list):
            self.type_includes = [str(t).lower() for t in raw_types]
        else:
            self.type_includes = [
                t.strip().lower() for t in str(raw_types).split(",") if t.strip()
            ]
        self.enrich_abstracts: bool = bool(self.params.get("enrich_abstracts", False))
        self.s2_api_key: Optional[str] = self.params.get("s2_api_key")
        self.s2_min_interval: float = float(
            self.params.get("s2_min_interval", self.min_interval)
        )

    def fetch(self) -> List[Paper]:
        records = list(
            iter_dblp_publications(
                query=self.query,
                per_page=self.per_page,
                min_interval=self.min_interval,
                max_pages=self.max_pages,
            )
        )

        papers: List[Dict[str, Any]] = []
        for r in records:
            if self.year and r.get("year") != str(self.year):
                continue
            if self.type_includes and (r.get("type") or "").lower() not in self.type_includes:
                continue
            venue = (r.get("venue") or "")
            if self.venue_contains and self.venue_contains not in venue:
                continue
            papers.append(r)
            if len(papers) >= self.limit:
                break

        detailed: List[Dict[str, Any]] = []
        last_ts: float | None = None
        for p in papers:
            key = p.get("key")
            if not key:
                continue
            detail, last_ts = fetch_dblp_record_xml(
                key,
                min_interval=self.min_interval,
                last_ts=last_ts,
            )
            if detail:
                if self.enrich_abstracts and not detail.get("abstract"):
                    abstract = enrich_abstract_from_ee(
                        detail.get("ee", []),
                        title=detail.get("title", ""),
                        min_interval=self.s2_min_interval,
                        api_key=self.s2_api_key,
                    )
                    if abstract:
                        detail["abstract"] = abstract
                detailed.append(detail)

        return [self._to_paper(d) for d in detailed]

    def _to_paper(self, record: Dict[str, Any]) -> Paper:
        ee_list = record.get("ee") or []
        pdf_url = ee_list[0] if ee_list else None
        keywords = []
        venue = record.get("venue")
        if venue:
            keywords.append(venue)

        return Paper(
            id=record.get("key", ""),
            title=record.get("title", ""),
            abstract="",
            authors=record.get("authors", []),
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


def _normalize_authors(info: Dict[str, Any]) -> List[str]:
    authors = info.get("authors", {}).get("author", [])
    if isinstance(authors, dict):
        authors = [authors]
    if isinstance(authors, str):
        authors = [authors]
    normalized: List[str] = []
    for a in authors:
        if isinstance(a, dict):
            normalized.append(a.get("text") or a.get("name") or str(a))
        else:
            normalized.append(str(a))
    return normalized


def _normalize_ee(info: Dict[str, Any]) -> List[str]:
    ee = info.get("ee", [])
    if isinstance(ee, str):
        return [ee]
    if isinstance(ee, list):
        return [str(x) for x in ee]
    return []


def _extract_openreview_id(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        if "openreview.net" not in parsed.netloc:
            return None
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            return qs["id"][0]
    except Exception:
        return None
    return None


def _extract_arxiv_id(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        if "arxiv.org" not in parsed.netloc:
            return None
        path = parsed.path.strip("/").split("/")
        if not path:
            return None
        if path[0] in {"abs", "pdf"} and len(path) >= 2:
            arxiv_id = path[1]
            return arxiv_id.replace(".pdf", "")
    except Exception:
        return None
    return None


def _extract_doi(ee_list: List[str]) -> Optional[str]:
    for ee in ee_list:
        if "doi.org/" in ee:
            return ee.split("doi.org/")[-1].strip()
        if ee.startswith("doi:"):
            return ee.replace("doi:", "").strip()
    return None


def _fetch_openreview_abstract(
    note_id: str, timeout: float = 20.0, api_key: Optional[str] = None
) -> Optional[str]:
    url = "https://api2.openreview.net/notes"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(url, params={"id": note_id}, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        return None
    data = resp.json()
    notes = data.get("notes") or []
    if not notes:
        return None
    content = notes[0].get("content", {})
    abstract = content.get("abstract", {}).get("value")
    if isinstance(abstract, str) and abstract.strip():
        return abstract.strip()
    return None


def _fetch_arxiv_abstract(arxiv_id: str, timeout: float = 20.0) -> Optional[str]:
    url = "https://export.arxiv.org/api/query"
    resp = requests.get(url, params={"id_list": arxiv_id}, timeout=timeout)
    if resp.status_code != 200:
        return None
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return None
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None
    summary = entry.find("atom:summary", ns)
    if summary is not None and summary.text:
        return summary.text.strip()
    return None


def _fetch_cvf_abstract(url: str, timeout: float = 20.0) -> Optional[str]:
    resp = requests.get(url, timeout=timeout)
    if resp.status_code != 200:
        return None
    text = resp.text
    for marker in [
        'id="abstract"',
        'class="abstract"',
        "Abstract</h3>",
        "Abstract</h4>",
    ]:
        idx = text.find(marker)
        if idx == -1:
            continue
        snippet = text[idx : idx + 2000]
        cleaned = (
            snippet.replace("<br>", " ")
            .replace("<br/>", " ")
            .replace("<br />", " ")
        )
        cleaned = _strip_html(cleaned)
        if "Abstract" in cleaned:
            cleaned = cleaned.split("Abstract", 1)[-1].strip()
        if cleaned:
            return cleaned[:2000].strip()
    return None


def _fetch_s2_abstract_by_doi(
    doi: str, timeout: float = 20.0, api_key: Optional[str] = None
) -> Optional[str]:
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    params = {"fields": "title,abstract"}
    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    if resp.status_code != 200:
        return None
    data = resp.json()
    abstract = data.get("abstract")
    if isinstance(abstract, str) and abstract.strip():
        return abstract.strip()
    return None


def _fetch_s2_abstract_by_title(
    title: str, timeout: float = 20.0, api_key: Optional[str] = None
) -> Optional[str]:
    if not title:
        return None
    query = quote(title)
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={query}&limit=1&fields=title,abstract"
    )
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        return None
    data = resp.json()
    items = data.get("data") or []
    if not items:
        return None
    abstract = items[0].get("abstract")
    if isinstance(abstract, str) and abstract.strip():
        return abstract.strip()
    return None


def _strip_html(text: str) -> str:
    out = []
    in_tag = False
    for ch in text:
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return " ".join("".join(out).split())


def enrich_abstract_from_ee(
    ee_list: List[str],
    title: str = "",
    min_interval: float = 1.0,
    api_key: Optional[str] = None,
    timeout: float = 20.0,
) -> Optional[str]:
    last_ts: float | None = None
    for ee in ee_list:
        if "openreview.net" in ee:
            note_id = _extract_openreview_id(ee)
            if note_id:
                last_ts = _sleep_with_min_interval(last_ts, min_interval)
                abstract = _fetch_openreview_abstract(
                    note_id, timeout=timeout, api_key=api_key
                )
                if abstract:
                    return abstract
        if "arxiv.org" in ee:
            arxiv_id = _extract_arxiv_id(ee)
            if arxiv_id:
                last_ts = _sleep_with_min_interval(last_ts, min_interval)
                abstract = _fetch_arxiv_abstract(arxiv_id, timeout=timeout)
                if abstract:
                    return abstract
        if "openaccess.thecvf.com" in ee:
            last_ts = _sleep_with_min_interval(last_ts, min_interval)
            abstract = _fetch_cvf_abstract(ee, timeout=timeout)
            if abstract:
                return abstract
    doi = _extract_doi(ee_list)
    if doi:
        last_ts = _sleep_with_min_interval(last_ts, min_interval)
        abstract = _fetch_s2_abstract_by_doi(doi, timeout=timeout, api_key=api_key)
        if abstract:
            return abstract
    if title:
        last_ts = _sleep_with_min_interval(last_ts, min_interval)
        abstract = _fetch_s2_abstract_by_title(title, timeout=timeout, api_key=api_key)
        if abstract:
            return abstract
    return None


def _parse_hits(payload: Dict[str, Any]) -> tuple[int, List[Dict[str, Any]]]:
    hits = payload.get("result", {}).get("hits", {})
    total = int(hits.get("@total", 0) or 0)
    raw_hits = hits.get("hit", [])
    if isinstance(raw_hits, dict):
        raw_hits = [raw_hits]
    records: List[Dict[str, Any]] = []
    for hit in raw_hits:
        info = hit.get("info", {})
        records.append(
            {
                "key": info.get("key"),
                "title": info.get("title"),
                "authors": _normalize_authors(info),
                "year": info.get("year"),
                "venue": info.get("venue"),
                "type": info.get("type"),
                "pages": info.get("pages"),
                "url": info.get("url"),
                "ee": _normalize_ee(info),
            }
        )
    return total, records


def iter_dblp_publications(
    query: str,
    per_page: int = 100,
    min_interval: float = 1.0,
    max_pages: Optional[int] = None,
    timeout: float = 20.0,
    base_urls: Optional[List[str]] = None,
) -> Iterable[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "WhiteNote-dblp-crawler/0.1 (contact: admin@example.com)",
            "Accept": "application/json",
        }
    )

    start = 0
    page = 0
    total = None
    last_ts: float | None = None

    urls = base_urls or DBLP_SEARCH_URLS

    while True:
        if max_pages is not None and page >= max_pages:
            break

        last_ts = _sleep_with_min_interval(last_ts, min_interval)

        params = {
            "q": query,
            "format": "json",
            "h": per_page,
            "f": start,
        }
        resp = None
        last_error: Optional[Exception] = None
        for base_url in urls:
            try:
                resp = session.get(base_url, params=params, timeout=timeout)
                break
            except requests.RequestException as exc:
                last_error = exc
                continue

        if resp is None:
            raise requests.RequestException("All dblp endpoints failed") from last_error

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait_s = float(retry_after) if retry_after else min_interval
            time.sleep(wait_s)
            continue

        resp.raise_for_status()
        payload = resp.json()

        total, records = _parse_hits(payload)
        if not records:
            break

        for r in records:
            yield r

        start += len(records)
        page += 1
        if total is not None and start >= total:
            break


def _parse_record_xml(xml_text: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_text)
    record = next(iter(root), None)
    if record is None:
        return {}

    data: Dict[str, Any] = {
        "key": record.get("key"),
        "type": record.tag,
        "mdate": record.get("mdate"),
        "authors": [],
        "ee": [],
        "url": [],
    }

    for child in record:
        tag = child.tag
        text = (child.text or "").strip()
        if not text:
            continue
        if tag in {"author", "editor"}:
            data["authors"].append(text)
        elif tag == "ee":
            data["ee"].append(text)
        elif tag == "url":
            data["url"].append(text)
        else:
            data[tag] = text

    if "booktitle" in data:
        data["venue"] = data["booktitle"]
    elif "journal" in data:
        data["venue"] = data["journal"]

    return data


def fetch_dblp_record_xml(
    key: str,
    timeout: float = 20.0,
    min_interval: float = 1.0,
    base_urls: Optional[List[str]] = None,
    last_ts: float | None = None,
) -> tuple[Dict[str, Any], float]:
    last_ts = _sleep_with_min_interval(last_ts, min_interval)
    urls = base_urls or DBLP_REC_URLS
    last_error: Optional[Exception] = None
    for base_url in urls:
        try:
            url = f"{base_url}/{key}.xml"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_s = float(retry_after) if retry_after else min_interval
                time.sleep(wait_s)
                return fetch_dblp_record_xml(
                    key,
                    timeout=timeout,
                    min_interval=min_interval,
                    base_urls=base_urls,
                    last_ts=last_ts,
                )
            resp.raise_for_status()
            return _parse_record_xml(resp.text), time.time()
        except requests.RequestException as exc:
            last_error = exc
            continue

    raise requests.RequestException("All dblp record endpoints failed") from last_error
