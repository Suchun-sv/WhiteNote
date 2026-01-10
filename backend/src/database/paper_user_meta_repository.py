from typing import List
from src.database.db.session import SessionLocal
from src.database.db.models import PaperUserMeta


class PaperUserMetaRepository:
    """
    Manage user-specific metadata for papers
    """

    def set_like(self, user_id: str, paper_id: str, liked: bool) -> None:
        with SessionLocal() as db:
            meta = (
                db.query(PaperUserMeta)
                .filter_by(user_id=user_id, paper_id=paper_id)
                .first()
            )

            if not meta:
                meta = PaperUserMeta(
                    user_id=user_id,
                    paper_id=paper_id,
                )
                db.add(meta)

            meta.liked = liked
            db.commit()

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