"""
Demo: use Semantic Scholar bulk search to fetch CVPR 2025 main-conference list,
then (optionally) batch-fetch details using /paper/batch.

Anonymous requests only (no API key).

Usage:
  python src/crawler/s2_bulk_demo.py
  python src/crawler/s2_bulk_demo.py --out /tmp/cvpr2025_s2_bulk.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict, Iterable, List, Optional

import requests


S2_BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"

DEFAULT_QUERY = ""
DEFAULT_YEAR = "2025"
DEFAULT_VENUE = "CVPR"
DEFAULT_MIN_INTERVAL = 1.0
DEFAULT_BATCH_SIZE = 500


def _sleep_with_min_interval(last_ts: float | None, min_interval: float) -> float:
    now = time.time()
    if last_ts is None:
        return now
    elapsed = now - last_ts
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.time()


def fetch_bulk(
    query: str,
    year: str,
    venue: str,
    fields: str,
    min_interval: float,
) -> List[Dict[str, object]]:
    token: Optional[str] = None
    last_ts: float | None = None
    out: List[Dict[str, object]] = []

    while True:
        last_ts = _sleep_with_min_interval(last_ts, min_interval)
        params = {"year": year, "venue": venue, "fields": fields, "limit": 1000}
        if query:
            params["query"] = query
        if token:
            params["token"] = token
        retries = 0
        while True:
            resp = requests.get(S2_BULK_URL, params=params, timeout=30)
            if resp.status_code == 429:
                retries += 1
                if retries > 5:
                    raise RuntimeError("Semantic Scholar rate limit exceeded")
                wait_s = min(5 * (2 ** (retries - 1)), 60)
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
            payload = resp.json()
            break
        data = payload.get("data") or []
        if isinstance(data, list):
            out.extend(data)
        token = payload.get("token")
        if not token:
            break
    return out


def filter_main_cvpr(records: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for r in records:
        venue = (r.get("venue") or "").strip()
        pub = r.get("publicationVenue") or {}
        pub_name = ""
        pub_alt = []
        if isinstance(pub, dict):
            pub_name = str(pub.get("name") or "").strip()
            alt = pub.get("alternate_names") or []
            if isinstance(alt, list):
                pub_alt = [str(a).strip() for a in alt]

        hay = " ".join([venue, pub_name] + pub_alt).lower()
        if "workshop" in hay:
            continue
        if "computer vision and pattern recognition" in hay or "cvpr" in hay:
            out.append(r)
    return out


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_batch(
    paper_ids: List[str],
    fields: str,
    min_interval: float,
    batch_size: int,
    max_retries: int = 5,
) -> List[Dict[str, object]]:
    last_ts: float | None = None
    out: List[Dict[str, object]] = []

    for batch in chunked(paper_ids, batch_size):
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
                out.extend(data)
            break

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic Scholar bulk CVPR 2025 demo")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--year", default=DEFAULT_YEAR)
    parser.add_argument("--venue", default=DEFAULT_VENUE)
    parser.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--out",
        default="backend/tmp/cvpr2025_s2_bulk.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument(
        "--with-batch",
        action="store_true",
        help="Also fetch batch details via /paper/batch",
    )
    args = parser.parse_args()

    bulk_fields = "paperId,title,year,venue,publicationVenue,url"
    records = fetch_bulk(
        query=args.query,
        year=args.year,
        venue=args.venue,
        fields=bulk_fields,
        min_interval=args.min_interval,
    )
    filtered = filter_main_cvpr(records)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for item in filtered:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"S2 bulk fetched: {len(records)}")
    print(f"S2 bulk filtered (main CVPR): {len(filtered)}")
    print(f"Wrote: {args.out}")

    if args.with_batch:
        paper_ids = [r.get("paperId") for r in filtered if r.get("paperId")]
        batch_fields = "title,abstract,url,openAccessPdf,externalIds,venue,publicationVenue,year"
        details = fetch_batch(
            paper_ids=paper_ids,
            fields=batch_fields,
            min_interval=args.min_interval,
            batch_size=args.batch_size,
        )
        out_details = args.out.replace(".jsonl", "_details.jsonl")
        with open(out_details, "w", encoding="utf-8") as f:
            for item in details:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Batch details: {len(details)}")
        print(f"Wrote: {out_details}")


if __name__ == "__main__":
    main()
