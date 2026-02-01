"""
One-time migration script: upload existing local PDFs and comics to MinIO.

Usage:
    cd backend
    uv run python -m src.scripts.migrate_to_minio
"""

import logging
from pathlib import Path

from src.config import Config
from src.service.storage_service import get_storage

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def migrate_pdfs(storage, pdf_dir: Path) -> int:
    if not pdf_dir.is_dir():
        logger.info(f"PDF directory not found: {pdf_dir}")
        return 0

    count = 0
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        paper_id = pdf_file.stem
        if storage.pdf_exists(paper_id):
            logger.info(f"  skip (exists): {pdf_file.name}")
            continue
        data = pdf_file.read_bytes()
        storage.upload_pdf(paper_id, data)
        count += 1
    return count


def migrate_comics(storage, img_dir: Path) -> int:
    if not img_dir.is_dir():
        logger.info(f"Image directory not found: {img_dir}")
        return 0

    count = 0
    for img_file in sorted(img_dir.glob("*_comic.*")):
        # Extract paper_id from filename like "2401.12345_comic.png"
        stem = img_file.stem  # "2401.12345_comic"
        if not stem.endswith("_comic"):
            continue
        paper_id = stem[: -len("_comic")]
        ext = img_file.suffix  # ".png" or ".jpg"

        if storage.comic_exists(paper_id):
            logger.info(f"  skip (exists): {img_file.name}")
            continue
        data = img_file.read_bytes()
        storage.upload_comic(paper_id, data, ext)
        count += 1
    return count


def main() -> None:
    storage = get_storage()
    logger.info("Starting migration to MinIO...")

    pdf_dir = Path(Config.pdf_save_path)
    logger.info(f"Migrating PDFs from {pdf_dir}")
    pdf_count = migrate_pdfs(storage, pdf_dir)
    logger.info(f"  PDFs uploaded: {pdf_count}")

    img_dir = Path(Config.image_save_path)
    logger.info(f"Migrating comics from {img_dir}")
    comic_count = migrate_comics(storage, img_dir)
    logger.info(f"  Comics uploaded: {comic_count}")

    logger.info(f"Migration complete. {pdf_count} PDFs, {comic_count} comics.")


if __name__ == "__main__":
    main()
