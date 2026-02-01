from __future__ import annotations
import io
import time
import logging
from typing import Iterable
import requests

from .storage_service import get_storage

logger = logging.getLogger(__name__)


class PdfDownloader:
    def __init__(
        self,
        timeout: int = 30,
        retries: int = 3,
        min_interval: int = 10,
    ):
        from ..config import Config
        self.timeout = timeout
        self.retries = retries
        self.min_interval = min_interval
        self._storage = get_storage()

    def _looks_like_pdf(self, content: bytes, content_type: str | None):
        if content.startswith(b"%PDF-"):
            return True
        if content_type and "application/pdf" in content_type.lower():
            return True
        return False

    def _download_one(self, url: str, paper_id: str) -> None:
        if self._storage.pdf_exists(paper_id):
            logger.info(f"Skip (exists in MinIO): {paper_id}.pdf")
            return

        for attempt in range(1, self.retries + 1):
            try:
                logger.info(f"Start [{attempt}/{self.retries}]: {url}")

                r = requests.get(url, timeout=self.timeout, stream=True)
                r.raise_for_status()

                content_type = r.headers.get("Content-Type", "")

                # Read into memory
                buf = io.BytesIO()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        buf.write(chunk)

                pdf_bytes = buf.getvalue()

                if not self._looks_like_pdf(pdf_bytes[:16384], content_type):
                    logger.warning(f"Not a PDF (maybe CAPTCHA): {url}")
                    return

                # Upload to MinIO
                self._storage.upload_pdf(paper_id, pdf_bytes)
                logger.info(f"Saved PDF to MinIO: {paper_id}.pdf")
                break

            except Exception as e:
                logger.warning(f"Error [{attempt}/{self.retries}]: {url} | {e}")

                if attempt == self.retries:
                    logger.error(f"Failed: {url}")
                    break

                wait = max(self.min_interval, 2 ** attempt)
                logger.info(f"Retry in {wait}s...")
                time.sleep(wait)

    def download_one(self, url: str, id: str):
        self._download_one(url, id)

    def download_all(self, items: Iterable[tuple[str, str]]):
        items = list(items)
        if not items:
            logger.info("No download tasks.")
            return

        logger.info(f"Total tasks: {len(items)}")

        for url, paper_id in items:
            self._download_one(url, paper_id)
