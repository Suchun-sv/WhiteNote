from __future__ import annotations

from typing import List, Optional, Any, Union
from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from src.model.paper import Paper
from src.database.db.session import SessionLocal
from src.database.db.models import PaperRow


class PaperRepository:
    """
    Postgres-only repository for Paper.

    Drop-in replacement for JsonStore with identical semantics.
    All JSONB data stored here is guaranteed to be JSON-serializable.
    """

    # =====================================================
    # Basic CRUD
    # =====================================================

    def save(self, paper: Paper) -> None:
        """
        Insert or update a Paper (full overwrite).
        """
        with SessionLocal() as db:
            row = PaperRow(
                id=paper.id,
                paper=paper.model_dump(mode="json"),  
                title=paper.title,
                created_at=paper.created_at,
                updated_at=datetime.utcnow(),
                arxiv_entry_id=paper.arxiv_entry_id,
                arxiv_published=paper.arxiv_published,
                arxiv_updated=paper.arxiv_updated,
            )
            db.merge(row)
            db.commit()

    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """
        Get a Paper by id.
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return None
            return Paper.model_validate(row.paper)

    def get_all_papers(self) -> List[Paper]:
        """
        Load all papers from database.

        ⚠️ Debug / small dataset only.
        """
        with SessionLocal() as db:
            rows = db.execute(select(PaperRow)).scalars().all()
            return [Paper.model_validate(r.paper) for r in rows]

    # =====================================================
    # Insert-only logic (crawl / ingest)
    # =====================================================

    def insert_new_papers(self, new_papers: List[Paper]) -> List[Paper]:
        """
        Insert only new papers (by Paper.id).
        """
        if not new_papers:
            return []

        paper_ids = [p.id for p in new_papers if p.id]

        with SessionLocal() as db:
            existing_ids = set(
                id_
                for (id_,) in db.execute(
                    select(PaperRow.id).where(PaperRow.id.in_(paper_ids))
                )
            )

            inserted: List[Paper] = []

            for p in new_papers:
                if not p.id or p.id in existing_ids:
                    continue

                row = PaperRow(
                    id=p.id,
                    paper=p.model_dump(mode="json"),
                    title=p.title,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    arxiv_entry_id=p.arxiv_entry_id,
                    arxiv_published=p.arxiv_published,
                    arxiv_updated=p.arxiv_updated,
                )
                db.add(row)
                inserted.append(p)

            db.commit()
            return inserted

    # =====================================================
    # Partial update (enrichment / metadata)
    # =====================================================

    def update_paper_field(self, paper_id: str, field: str, value: Any) -> None:
        """
        Update a single field inside Paper JSON.
        """
        if field not in Paper.model_fields:
            raise ValueError(f"Field '{field}' is not a valid Paper field")

        with SessionLocal() as db:
            row: Optional[PaperRow] = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)

            if isinstance(value, datetime):
                value = value.isoformat()

            paper[field] = value
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()

    # =====================================================
    # Pagination & sorting (UI / API)
    # =====================================================

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> List[Paper]:
        """
        List papers with pagination and sorting.
        """
        with SessionLocal() as db:
            query = db.query(PaperRow)

            sort_col = getattr(PaperRow, sort_by, PaperRow.created_at)
            query = (
                query.order_by(sort_col.desc())
                if order == "desc"
                else query.order_by(sort_col.asc())
            )

            rows = (
                query
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return [Paper.model_validate(r.paper) for r in rows]

    # =====================================================
    # Enrichment helpers (daily job)
    # =====================================================

    def list_missing_ai_abstract(self, limit: int = -1) -> List[Paper]:
        """
        List papers without ai_abstract.
        """
        with SessionLocal() as db:
            query = (
                db.query(PaperRow)
                .filter(
                    PaperRow.paper.op("->>")("ai_abstract").is_(None), # JSON null
                )
                .order_by(PaperRow.created_at.asc())
            )

            if limit > 0:
                query = query.limit(limit)

            rows = query.all()
            return [Paper.model_validate(r.paper) for r in rows]
    
    def update_ai_abstract(self, paper_id: str, ai_abstract: str, provider: str) -> None:
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)
            paper["ai_abstract"] = ai_abstract
            paper["ai_abstract_provider"] = provider
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()
    
    def list_missing_ai_title(self, limit: int = -1) -> List[Paper]:
        """
        List papers without ai_title.
        """
        with SessionLocal() as db:
            query = (
                db.query(PaperRow)
                .filter(PaperRow.paper.op("->>")("ai_title").is_(None))
                .order_by(PaperRow.created_at.asc())
            )

            if limit > 0:
                query = query.limit(limit)

            rows = query.all()
            return [Paper.model_validate(r.paper) for r in rows]
        
    def update_ai_title(self, paper_id: str, ai_title: str, provider: str) -> None:
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)   # ⭐ 拷贝一份新的 dict
            paper["ai_title"] = ai_title
            paper["ai_title_provider"] = provider
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper         # ⭐ 整体赋值（SQLAlchemy 能识别）
            row.updated_at = datetime.utcnow()

            db.commit()

    def list_missing_ai_summary(self, limit: int = 5) -> List[Paper]:
        """
        List papers without ai_summary.
        """
        with SessionLocal() as db:
            rows = (
                db.query(PaperRow)
                .filter(
                    (PaperRow.paper["ai_summary"].is_(None))
                    | (PaperRow.paper.op("->>")("ai_summary") == "")
                )
                .order_by(PaperRow.created_at.asc())
                .limit(limit)
                .all()
            )
            return [Paper.model_validate(r.paper) for r in rows]

    def update_full_text(self, paper_id: str, full_text: str) -> None:
        """
        Update extracted full text.
        """
        self.update_paper_field(paper_id, "full_text", full_text)

    def update_ai_summary(
        self,
        paper_id: str,
        ai_summary: str,
        provider: str,
    ) -> None:
        """
        Update ai_summary and its provider.
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)
            paper["ai_summary"] = ai_summary
            paper["ai_summary_provider"] = provider
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()

    # =====================================================
    # Job status tracking
    # =====================================================

    def update_summary_job_status(self, paper_id: str, status: str) -> None:
        """
        Update summary_job_status field.

        Status values: pending | running | completed | failed
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)
            paper["summary_job_status"] = status
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()

    def get_summary_job_status(self, paper_id: str) -> Optional[str]:
        """
        Get summary_job_status for a paper.
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return None
            return row.paper.get("summary_job_status")

    def update_comic_job_status(self, paper_id: str, status: str) -> None:
        """
        Update comic_job_status field.

        Status values: pending | running | completed | failed
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)
            paper["comic_job_status"] = status
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()

    def get_comic_job_status(self, paper_id: str) -> Optional[str]:
        """
        Get comic_job_status for a paper.
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return None
            return row.paper.get("comic_job_status")

    # =====================================================
    # Favorite folders
    # =====================================================

    def add_to_folder(self, paper_id: str, folder_name: str) -> bool:
        """
        Add a paper to a favorite folder.

        Returns:
            True if added (was not already in folder), False otherwise
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return False

            paper = dict(row.paper)
            folders: List[str] = paper.get("favorite_folders") or []

            if folder_name in folders:
                return False  # Already in folder

            folders.append(folder_name)
            paper["favorite_folders"] = folders

            # Set favorited_at if this is the first folder
            if len(folders) == 1:
                paper["favorited_at"] = datetime.utcnow().isoformat()

            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()
            return True

    def remove_from_folder(self, paper_id: str, folder_name: str) -> bool:
        """
        Remove a paper from a favorite folder.

        Returns:
            True if removed, False if not found
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return False

            paper = dict(row.paper)
            folders: List[str] = paper.get("favorite_folders") or []

            if folder_name not in folders:
                return False

            folders.remove(folder_name)
            paper["favorite_folders"] = folders

            # Clear favorited_at if no folders left
            if not folders:
                paper["favorited_at"] = None

            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()
            return True

    def list_by_folder(self, folder_name: str) -> List[Paper]:
        """
        List all papers in a specific folder.
        """
        with SessionLocal() as db:
            # Query papers where favorite_folders contains folder_name
            rows = (
                db.query(PaperRow)
                .filter(
                    PaperRow.paper["favorite_folders"].contains([folder_name])
                )
                .order_by(PaperRow.updated_at.desc())
                .all()
            )
            return [Paper.model_validate(r.paper) for r in rows]

    def get_all_folders(self) -> List[str]:
        """
        Get all unique folder names across all papers.
        """
        with SessionLocal() as db:
            rows = db.query(PaperRow).all()

            all_folders: set[str] = set()
            for row in rows:
                folders = row.paper.get("favorite_folders") or []
                all_folders.update(folders)

            return sorted(all_folders)

    def get_folder_counts(self) -> dict[str, int]:
        """
        Get paper count for each folder.

        Returns:
            Dict mapping folder_name -> count
        """
        with SessionLocal() as db:
            rows = db.query(PaperRow).all()

            counts: dict[str, int] = {}
            for row in rows:
                folders = row.paper.get("favorite_folders") or []
                for folder in folders:
                    counts[folder] = counts.get(folder, 0) + 1

            return counts

    def rename_folder(self, old_name: str, new_name: str) -> int:
        """
        Rename a folder (batch update all related papers).

        Args:
            old_name: Current folder name
            new_name: New folder name

        Returns:
            Number of papers affected
        """
        if not new_name or not new_name.strip():
            return 0

        new_name = new_name.strip()

        if old_name == new_name:
            return 0

        with SessionLocal() as db:
            # Find all papers with the old folder name
            rows = (
                db.query(PaperRow)
                .filter(PaperRow.paper["favorite_folders"].contains([old_name]))
                .all()
            )

            count = 0
            for row in rows:
                paper = dict(row.paper)
                folders: List[str] = paper.get("favorite_folders") or []

                if old_name in folders:
                    # Replace old name with new name
                    idx = folders.index(old_name)
                    folders[idx] = new_name
                    paper["favorite_folders"] = folders
                    paper["updated_at"] = datetime.utcnow().isoformat()

                    row.paper = paper
                    row.updated_at = datetime.utcnow()
                    count += 1

            db.commit()
            return count

    def delete_folder(self, folder_name: str) -> int:
        """
        Delete a folder (remove from all papers).

        Args:
            folder_name: Folder name to delete

        Returns:
            Number of papers affected
        """
        with SessionLocal() as db:
            # Find all papers with this folder
            rows = (
                db.query(PaperRow)
                .filter(PaperRow.paper["favorite_folders"].contains([folder_name]))
                .all()
            )

            count = 0
            for row in rows:
                paper = dict(row.paper)
                folders: List[str] = paper.get("favorite_folders") or []

                if folder_name in folders:
                    folders.remove(folder_name)
                    paper["favorite_folders"] = folders

                    # Clear favorited_at if no folders left
                    if not folders:
                        paper["favorited_at"] = None

                    paper["updated_at"] = datetime.utcnow().isoformat()

                    row.paper = paper
                    row.updated_at = datetime.utcnow()
                    count += 1

            db.commit()
            return count

    def create_empty_folder(self, folder_name: str) -> bool:
        """
        Create an empty folder placeholder.
        
        Note: Since folders are virtual (derived from papers),
        we store empty folders in a special way - by adding
        a marker. For simplicity, we just return True here
        as folders are created when papers are added to them.
        
        Returns:
            True (folder "created" - will appear when paper is added)
        """
        # Folders are virtual - they exist when at least one paper has them
        # For "empty" folders, we could store them in a separate config,
        # but for now, just return True as a no-op
        return True

    # =====================================================
    # Dislike
    # =====================================================

    def mark_disliked(self, paper_id: str) -> None:
        """
        Mark a paper as disliked.
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)
            paper["is_disliked"] = True
            paper["disliked_at"] = datetime.utcnow().isoformat()
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()

    def unmark_disliked(self, paper_id: str) -> None:
        """
        Remove dislike mark from a paper.
        """
        with SessionLocal() as db:
            row = db.get(PaperRow, paper_id)
            if not row:
                return

            paper = dict(row.paper)
            paper["is_disliked"] = False
            paper["disliked_at"] = None
            paper["updated_at"] = datetime.utcnow().isoformat()

            row.paper = paper
            row.updated_at = datetime.utcnow()

            db.commit()

    def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        order: str = "desc",
        include_disliked: bool = False,
        include_favorite: bool = False,
        folder_filter: Optional[str] = None,
    ) -> List[Paper]:
        """
        List papers with filters for disliked and folder.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            sort_by: Field to sort by
            order: 'asc' or 'desc'
            include_disliked: If False, exclude disliked papers
            include_favorite: If False, exclude favorite papers
            folder_filter: If set, only return papers in this folder
        """
        with SessionLocal() as db:
            query = db.query(PaperRow)

            # Filter out disliked papers by default
            if not include_disliked:
                query = query.filter(
                    or_(
                        PaperRow.paper["is_disliked"].is_(None),
                        PaperRow.paper["is_disliked"].astext == "false",
                    )
                )

            # Filter by folder (takes priority over include_favorite)
            if folder_filter:
                # 当指定收藏夹时，只看该收藏夹内的论文
                query = query.filter(
                    PaperRow.paper["favorite_folders"].contains([folder_filter])
                )
            elif not include_favorite:
                # 只有在没有指定收藏夹筛选时，才过滤掉收藏的论文
                query = query.filter(
                    or_(
                        PaperRow.paper["favorite_folders"].is_(None),
                        PaperRow.paper["favorite_folders"].astext == "[]",
                    )
                )

            # Sorting
            sort_col = getattr(PaperRow, sort_by, PaperRow.created_at)
            query = (
                query.order_by(sort_col.desc())
                if order == "desc"
                else query.order_by(sort_col.asc())
            )

            # Pagination
            rows = (
                query
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return [Paper.model_validate(r.paper) for r in rows]

    def count_with_filters(
        self,
        include_disliked: bool = False,
        folder_filter: Optional[str] = None,
    ) -> int:
        """
        Count papers with filters (for pagination).
        """
        with SessionLocal() as db:
            query = db.query(PaperRow)

            if not include_disliked:
                query = query.filter(
                    or_(
                        PaperRow.paper["is_disliked"].is_(None),
                        PaperRow.paper["is_disliked"].astext == "false",
                    )
                )

            if folder_filter:
                query = query.filter(
                    PaperRow.paper["favorite_folders"].contains([folder_filter])
                )

            return query.count()