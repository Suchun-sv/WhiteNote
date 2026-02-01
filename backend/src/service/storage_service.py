"""
MinIO object storage service for PDFs and comic images.

Usage:
    from src.service.storage_service import get_storage

    storage = get_storage()
    storage.upload_pdf("2401.12345", pdf_bytes)
    pdf_bytes = storage.get_pdf("2401.12345")
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from minio import Minio
from minio.error import S3Error

from src.config import Config

logger = logging.getLogger(__name__)

_storage: Optional[StorageService] = None


class StorageService:
    """MinIO wrapper for PDF and comic storage."""

    def __init__(self) -> None:
        cfg = Config.minio
        self.client = Minio(
            cfg.endpoint,
            access_key=cfg.access_key,
            secret_key=cfg.secret_key,
            secure=cfg.secure,
        )
        self.pdf_bucket = cfg.pdf_bucket
        self.comic_bucket = cfg.comic_bucket
        self._ensure_buckets()

    def _ensure_buckets(self) -> None:
        for bucket in (self.pdf_bucket, self.comic_bucket):
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")

    # ── PDF operations ──────────────────────────────────────────

    def _pdf_key(self, paper_id: str) -> str:
        return f"{paper_id}.pdf"

    def upload_pdf(self, paper_id: str, data: bytes) -> None:
        key = self._pdf_key(paper_id)
        self.client.put_object(
            self.pdf_bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type="application/pdf",
        )
        logger.info(f"Uploaded PDF: {key}")

    def get_pdf(self, paper_id: str) -> bytes:
        key = self._pdf_key(paper_id)
        response = self.client.get_object(self.pdf_bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def pdf_exists(self, paper_id: str) -> bool:
        key = self._pdf_key(paper_id)
        try:
            self.client.stat_object(self.pdf_bucket, key)
            return True
        except S3Error:
            return False

    # ── Comic operations ────────────────────────────────────────

    def _comic_key(self, paper_id: str, ext: str = ".png") -> str:
        return f"{paper_id}_comic{ext}"

    def upload_comic(self, paper_id: str, data: bytes, ext: str = ".png") -> str:
        """Upload comic image bytes. Returns the object key."""
        key = self._comic_key(paper_id, ext)
        mime = "image/png" if ext == ".png" else "image/jpeg"
        self.client.put_object(
            self.comic_bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=mime,
        )
        logger.info(f"Uploaded comic: {key}")
        return key

    def get_comic(self, paper_id: str) -> tuple[bytes, str]:
        """Return (image_bytes, content_type). Tries .png then .jpg."""
        for ext, mime in [(".png", "image/png"), (".jpg", "image/jpeg")]:
            key = self._comic_key(paper_id, ext)
            try:
                response = self.client.get_object(self.comic_bucket, key)
                try:
                    return response.read(), mime
                finally:
                    response.close()
                    response.release_conn()
            except S3Error:
                continue
        raise FileNotFoundError(f"Comic not found for paper {paper_id}")

    def comic_exists(self, paper_id: str) -> bool:
        for ext in (".png", ".jpg"):
            key = self._comic_key(paper_id, ext)
            try:
                self.client.stat_object(self.comic_bucket, key)
                return True
            except S3Error:
                continue
        return False

    def get_existing_comic_key(self, paper_id: str) -> Optional[str]:
        """Return the object key of an existing comic, or None."""
        for ext in (".png", ".jpg"):
            key = self._comic_key(paper_id, ext)
            try:
                self.client.stat_object(self.comic_bucket, key)
                return key
            except S3Error:
                continue
        return None


def get_storage() -> StorageService:
    """Lazy singleton — initializes on first call."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
