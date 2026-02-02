"""
Demo: crawl conference metadata from dblp search API,
then fetch per-paper detail from the dblp record (XML) API.
Optionally enrich abstracts from external sources.

Polite usage:
- low request rate (default 1s between requests)
- handle HTTP 429 with Retry-After

Reference (dblp search API):
https://dblp.org/faq/How%2Bto%2Buse%2Bthe%2Bdblp%2Bsearch%2BAPI.html
"""

from __future__ import annotations

import argparse
import json
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, quote, urlparse

import requests


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
            # Keep last occurrence for simple scalar fields.
            data[tag] = text

    # Derive a human-friendly venue.
    if "booktitle" in data:
        data["venue"] = data["booktitle"]
    elif "journal" in data:
        data["venue"] = data["journal"]

    return data


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


def _fetch_openreview_abstract(note_id: str, timeout: float = 20.0) -> Optional[str]:
    url = "https://api2.openreview.net/notes"
    resp = requests.get(url, params={"id": note_id}, timeout=timeout)
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
    # Try common CVF patterns
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
        # naive strip tags
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


def _fetch_s2_abstract_by_doi(doi: str, timeout: float = 20.0) -> Optional[str]:
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    params = {"fields": "title,abstract"}
    resp = requests.get(url, params=params, timeout=timeout)
    if resp.status_code != 200:
        return None
    data = resp.json()
    abstract = data.get("abstract")
    if isinstance(abstract, str) and abstract.strip():
        return abstract.strip()
    return None


def _fetch_s2_abstract_by_title(title: str, timeout: float = 20.0) -> Optional[str]:
    if not title:
        return None
    query = quote(title)
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=1&fields=title,abstract"
    resp = requests.get(url, timeout=timeout)
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
    timeout: float = 20.0,
) -> Optional[str]:
    for ee in ee_list:
        if "openreview.net" in ee:
            note_id = _extract_openreview_id(ee)
            if note_id:
                abstract = _fetch_openreview_abstract(note_id, timeout=timeout)
                if abstract:
                    return abstract
        if "arxiv.org" in ee:
            arxiv_id = _extract_arxiv_id(ee)
            if arxiv_id:
                abstract = _fetch_arxiv_abstract(arxiv_id, timeout=timeout)
                if abstract:
                    return abstract
        if "openaccess.thecvf.com" in ee:
            abstract = _fetch_cvf_abstract(ee, timeout=timeout)
            if abstract:
                return abstract
    doi = _extract_doi(ee_list)
    if doi:
        abstract = _fetch_s2_abstract_by_doi(doi, timeout=timeout)
        if abstract:
            return abstract
    if title:
        abstract = _fetch_s2_abstract_by_title(title, timeout=timeout)
        if abstract:
            return abstract
    return None


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
            "User-Agent": "WhiteNote-cvpr-demo/0.1 (contact: admin@example.com)",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="dblp metadata demo")
    parser.add_argument(
        "--query",
        default="conf/icml/2025",
        help="dblp search query string",
    )
    parser.add_argument(
        "--year",
        default="2025",
        help="filter by year (string), empty to disable",
    )
    parser.add_argument(
        "--venue-contains",
        default="ICML",
        help="filter if venue contains this substring (case sensitive)",
    )
    parser.add_argument(
        "--type-includes",
        default="conference and workshop papers",
        help="comma-separated types to include (case-insensitive)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="results per page (max 1000)",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=1.0,
        help="seconds between requests",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="optional page cap for a quick test",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="limit to N papers after filtering",
    )
    parser.add_argument(
        "--enrich-abstracts",
        action="store_true",
        help="try to enrich abstracts from ee links (OpenReview/arXiv/CVF)",
    )
    parser.add_argument(
        "--out",
        default="",
        help="optional output jsonl file path",
    )
    args = parser.parse_args()

    records = list(
        iter_dblp_publications(
            query=args.query,
            per_page=args.per_page,
            min_interval=args.min_interval,
            max_pages=args.max_pages,
        )
    )

    year_filter = args.year.strip() if isinstance(args.year, str) else str(args.year)
    venue_filter = args.venue_contains
    type_filters = [
        t.strip().lower()
        for t in str(args.type_includes).split(",")
        if t.strip()
    ]

    # Filter to target papers (exclude editorship records).
    papers: List[Dict[str, Any]] = []
    for r in records:
        if year_filter and r.get("year") != year_filter:
            continue
        if type_filters and (r.get("type") or "").lower() not in type_filters:
            continue
        venue = (r.get("venue") or "")
        if venue_filter and venue_filter not in venue:
            continue
        papers.append(r)
        if len(papers) >= args.limit:
            break

    detailed: List[Dict[str, Any]] = []
    last_ts: float | None = None
    for p in papers:
        key = p.get("key")
        if not key:
            continue
        detail, last_ts = fetch_dblp_record_xml(
            key,
            min_interval=args.min_interval,
            last_ts=last_ts,
        )
        if detail:
            if args.enrich_abstracts:
                abstract = enrich_abstract_from_ee(
                    detail.get("ee", []),
                    title=detail.get("title", ""),
                )
                if abstract:
                    detail["abstract"] = abstract
            detailed.append(detail)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for r in detailed:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(detailed)} detailed records to {args.out}")
    else:
        print(f"Fetched {len(papers)} paper stubs")
        print(f"Fetched {len(detailed)} detailed records")
        print(json.dumps(detailed[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
