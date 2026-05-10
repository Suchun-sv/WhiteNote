from datetime import datetime
from typing import List
from src.database.db.session import SessionLocal
from src.database.db.models import PaperUserMeta


class PaperUserMetaRepository:
    """
    Manage user-specific metadata for papers
    """

    def _upsert(self, user_id: str, paper_id: str) -> PaperUserMeta:
        with SessionLocal() as db:
            meta = (
                db.query(PaperUserMeta)
                .filter_by(user_id=user_id, paper_id=paper_id)
                .first()
            )
            if not meta:
                meta = PaperUserMeta(user_id=user_id, paper_id=paper_id)
                db.add(meta)
                db.commit()
                db.refresh(meta)
            return meta

    def _set_flag(self, user_id: str, paper_id: str, field: str, value: bool) -> None:
        with SessionLocal() as db:
            meta = (
                db.query(PaperUserMeta)
                .filter_by(user_id=user_id, paper_id=paper_id)
                .first()
            )
            if not meta:
                meta = PaperUserMeta(user_id=user_id, paper_id=paper_id)
                db.add(meta)
            setattr(meta, field, value)
            meta.updated_at = datetime.utcnow()
            db.commit()

    def set_like(self, user_id: str, paper_id: str, liked: bool) -> None:
        self._set_flag(user_id, paper_id, "liked", liked)

    def set_later(self, user_id: str, paper_id: str, later: bool) -> None:
        self._set_flag(user_id, paper_id, "later", later)

    def set_related(self, user_id: str, paper_id: str, related: bool) -> None:
        self._set_flag(user_id, paper_id, "related", related)

    def get_meta(self, user_id: str, paper_id: str) -> dict:
        with SessionLocal() as db:
            meta = (
                db.query(PaperUserMeta)
                .filter_by(user_id=user_id, paper_id=paper_id)
                .first()
            )
            if not meta:
                return {"liked": False, "later": False, "related": False}
            return {
                "liked": bool(meta.liked),
                "later": bool(meta.later),
                "related": bool(meta.related),
            }

    def list_liked(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> List[str]:
        with SessionLocal() as db:
            rows = (
                db.query(PaperUserMeta.paper_id)
                .filter(
                    PaperUserMeta.user_id == user_id,
                    PaperUserMeta.liked.is_(True),
                )
                .order_by(PaperUserMeta.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return [r[0] for r in rows]