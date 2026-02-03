#!/usr/bin/env python3
"""
Clear stuck/running feed jobs from history.
Usage:
    python clear_stuck_jobs.py
"""

import sys
sys.path.insert(0, '/mnt/data/suchun/github/WhiteNote/backend')

from api.routes.tasks import _JOB_HISTORY

def main():
    print(f"Before cleanup: {len(_JOB_HISTORY)} jobs in history")
    
    # Remove all running feed jobs
    global _JOB_HISTORY
    original_count = len(_JOB_HISTORY)
    
    # Keep only completed/failed jobs, remove running ones
    _JOB_HISTORY = [
        job for job in _JOB_HISTORY 
        if job.get("status") != "running" or job.get("job_type") != "feed"
    ]
    
    removed = original_count - len(_JOB_HISTORY)
    print(f"Removed {removed} stuck 'running' feed jobs")
    print(f"After cleanup: {len(_JOB_HISTORY)} jobs in history")
    
    # Show remaining jobs
    print("\nRemaining jobs:")
    for job in _JOB_HISTORY[:10]:
        print(f"  - [{job.get('job_type')}] {job.get('job_id')[:30]}... status={job.get('status')}")

if __name__ == "__main__":
    main()
