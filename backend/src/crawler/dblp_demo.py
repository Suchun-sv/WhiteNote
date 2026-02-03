"""
Demo: fetch CVPR 2025 main-conference paper list from DBLP search API,
then batch-query Semantic Scholar for abstracts/links (anonymous).

Usage:
  python -m src.crawler.dblp_demo
  python -m src.crawler.dblp_demo --out backend/tmp/cvpr2025_s2.jsonl
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import argparse
import json
import os
import time
from urllib.parse import parse_qs, urlparse

import requests


DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"

DEFAULT_QUERY = "conf/cvpr/2025"
DEFAULT_PER_PAGE = 1000
DEFAULT_MIN_INTERVAL = 1.0
DEFAULT_BATCH_SIZE = 500


@dataclass
class DblpRecord:
    key: str
    title: str
    year: str
    venue: str
    type: str
    ee: List[str]


def _sleep_with_min_interval(last_ts: float | None, min_interval: float) -> float:
    now = time.time()
    if last_ts is None:
        return now
    elapsed = now - last_ts
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.time()


def _normalize_ee(info: Dict[str, object]) -> List[str]:
    ee = info.get("ee")
    if isinstance(ee, str):
        return [ee]
    if isinstance(ee, list):
        return [str(x) for x in ee]
    return []


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


def fetch_dblp_records(
    query: str,
    per_page: int,
    min_interval: float,
) -> List[DblpRecord]:
    start = 0
    last_ts: float | None = None
    records: List[DblpRecord] = []

    while True:
        last_ts = _sleep_with_min_interval(last_ts, min_interval)
        params = {"q": query, "format": "json", "h": per_page, "f": start}
        resp = requests.get(DBLP_SEARCH_URL, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        hits = payload.get("result", {}).get("hits", {})
        raw = hits.get("hit", [])
        if isinstance(raw, dict):
            raw = [raw]
        if not raw:
            break
        for hit in raw:
            info = hit.get("info", {})
            records.append(
                DblpRecord(
                    key=str(info.get("key", "")),
                    title=str(info.get("title", "")),
                    year=str(info.get("year", "")),
                    venue=str(info.get("venue", "")),
                    type=str(info.get("type", "")),
                    ee=_normalize_ee(info),
                )
            )
        start += len(raw)
        total = int(hits.get("@total", 0) or 0)
        if start >= total:
            break

    return records


def filter_main_cvpr_papers(records: Iterable[DblpRecord]) -> List[DblpRecord]:
    out: List[DblpRecord] = []
    for r in records:
        if r.year != "2025":
            continue
        if r.type.lower().strip() == "editorship":
            continue
        if r.venue.strip() != "CVPR":
            continue
        out.append(r)
    return out


def build_s2_ids(records: Iterable[DblpRecord]) -> Tuple[List[str], Dict[str, DblpRecord]]:
    ids: List[str] = []
    id_to_record: Dict[str, DblpRecord] = {}
    for r in records:
        doi = _extract_doi(r.ee)
        if doi:
            s2id = f"DOI:{doi}"
            ids.append(s2id)
            id_to_record[s2id] = r
            continue
        arxiv_id = None
        for ee in r.ee:
            arxiv_id = _extract_arxiv_id(ee)
            if arxiv_id:
                break
        if arxiv_id:
            s2id = f"ARXIV:{arxiv_id}"
            ids.append(s2id)
            id_to_record[s2id] = r
            continue
    return ids, id_to_record


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_s2_batch(
    ids: List[str],
    fields: str,
    batch_size: int,
    min_interval: float = 1.0,
    max_retries: int = 5,
) -> List[Dict[str, object]]:
    last_ts: float | None = None
    all_results: List[Dict[str, object]] = []

    for batch in chunked(ids, batch_size):
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
                if retries > max_retries:
                    raise RuntimeError("Semantic Scholar rate limit exceeded")
                wait_s = min(5 * (2 ** (retries - 1)), 60)
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                all_results.extend(data)
            break

    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(description="DBLP -> Semantic Scholar batch demo")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE)
    parser.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--out",
        default="backend/tmp/cvpr2025_s2.jsonl",
        help="Output JSONL path",
    )
    args = parser.parse_args()

    records = fetch_dblp_records(args.query, args.per_page, args.min_interval)
    papers = filter_main_cvpr_papers(records)
    ids, id_to_record = build_s2_ids(papers)

    print(f"DBLP total records: {len(records)}")
    print(f"Main-conference papers (CVPR, 2025): {len(papers)}")
    print(f"S2 IDs (DOI/ARXIV only): {len(ids)}")

    fields = "title,abstract,url,openAccessPdf,externalIds"
    results = fetch_s2_batch(
        ids,
        fields=fields,
        batch_size=args.batch_size,
        min_interval=args.min_interval,
    )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"S2 results: {len(results)}")
    print(f"Wrote: {args.out}")

    # Show first two results (if any)
    for i, item in enumerate(results[:2], 1):
        ext = item.get("externalIds") or {}
        match_id = None
        if isinstance(ext, dict):
            if ext.get("DOI"):
                match_id = f"DOI:{ext.get('DOI')}"
            elif ext.get("ArXiv"):
                match_id = f"ARXIV:{ext.get('ArXiv')}"
        src = id_to_record.get(match_id) if match_id else None
        print("---", i)
        print("s2_title:", item.get("title"))
        print("s2_url:", item.get("url"))
        print("s2_openAccessPdf:", item.get("openAccessPdf"))
        print("s2_abstract:", (item.get("abstract") or "")[:200])
        if src:
            print("dblp_key:", src.key)
            print("dblp_title:", src.title)


if __name__ == "__main__":
    main()
