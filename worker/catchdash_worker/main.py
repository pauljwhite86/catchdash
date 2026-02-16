from __future__ import annotations

import logging
import time

from catchdash_worker.config import settings
from catchdash_worker.queue.backend_api import BackendQueueAPI
from catchdash_worker.runners.dispatcher import run_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def run_worker() -> None:
    api = BackendQueueAPI(settings.backend_base_url, timeout_seconds=settings.http_timeout_seconds)
    logger.info("worker started id=%s backend=%s", settings.worker_id, settings.backend_base_url)
    while True:
        try:
            jobs = api.list_jobs()
            queued = [row for row in jobs if row.get("status") == "queued"]
            logger.info("worker poll queued=%s", len(queued))
            for job in queued:
                run_job(api, job)
        except Exception as exc:
            logger.exception("worker loop error: %s", exc)
        time.sleep(max(1, settings.poll_seconds))


if __name__ == "__main__":
    run_worker()
