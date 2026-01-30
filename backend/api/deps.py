from typing import Generator

from src.database.db.session import SessionLocal
from src.database.paper_repository import PaperRepository


def get_db() -> Generator:
    """Yield a SQLAlchemy session (for future use)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_paper_repo() -> PaperRepository:
    """Return a PaperRepository instance (stateless, safe to create per-request)."""
    return PaperRepository()
