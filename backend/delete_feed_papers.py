#!/usr/bin/env python3
"""
Delete all papers from a specific feed.

Usage:
    python delete_feed_papers.py cvpr-2025
"""

import sys
from src.database.paper_repository import PaperRepository

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_feed_papers.py <feed_id>")
        print("Example: python delete_feed_papers.py cvpr-2025")
        sys.exit(1)
    
    feed_id = sys.argv[1]
    
    repo = PaperRepository()
    
    # First count papers
    count = repo.count_with_filters(feed=feed_id, include_disliked=True, include_favorite=True)
    print(f"Found {count} papers from feed '{feed_id}'")
    
    if count == 0:
        print("No papers to delete.")
        return
    
    # Confirm deletion
    confirm = input(f"Are you sure you want to delete all {count} papers from '{feed_id}'? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return
    
    # Delete papers
    deleted = repo.delete_by_feed(feed_id)
    print(f"Deleted {deleted} papers from feed '{feed_id}'")

if __name__ == "__main__":
    main()
