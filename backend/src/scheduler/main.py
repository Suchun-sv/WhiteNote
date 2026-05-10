"""Foreground entrypoint for APScheduler — used as a docker-compose service.

`SchedulerService` uses BackgroundScheduler; this wrapper keeps the process
alive so the container doesn't immediately exit.
"""
from __future__ import annotations

import logging
import signal
import sys
import time

from src.scheduler.scheduler_service import SchedulerService


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("whitenote.scheduler")

    service = SchedulerService()
    service.start()

    stopping = {"flag": False}

    def _stop(signum, frame):
        logger.info("Received signal %s, shutting down scheduler...", signum)
        stopping["flag"] = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while not stopping["flag"]:
            time.sleep(1)
    finally:
        service.shutdown()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
