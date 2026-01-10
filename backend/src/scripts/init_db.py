"""
Initialize database schema.

Run ONCE when:
- first local setup
- new environment deployment
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database.db.models import Base
from src.database.db.session import engine


def main():
    print("🔧 Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema initialized.")


if __name__ == "__main__":
    main()