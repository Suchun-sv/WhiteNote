"""
Add `feed` column to `papers` table if missing.

Run once after pulling the feed feature. Safe to run multiple times
(no-op if column already exists).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from src.database.db.session import engine


def main() -> None:
    with engine.connect() as conn:
        # Check if column exists (PostgreSQL)
        r = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'papers' AND column_name = 'feed'
                """
            )
        )
        if r.scalar() is not None:
            print("Column papers.feed already exists. Skipping.")
            return

        print("Adding column papers.feed ...")
        conn.execute(
            text("ALTER TABLE papers ADD COLUMN feed TEXT DEFAULT 'arxiv'")
        )
        conn.commit()
        print("Column added.")

        # Create index for filter/sort
        print("Creating index ix_papers_feed ...")
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_papers_feed ON papers (feed)")
        )
        conn.commit()
        print("Done.")


if __name__ == "__main__":
    main()
