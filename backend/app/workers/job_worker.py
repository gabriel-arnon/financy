from __future__ import annotations

import argparse
import time

from app.api.deps import get_open_finance_service, repository
from app.services.job_worker_service import JobWorkerService


def build_worker() -> JobWorkerService:
    return JobWorkerService(repository=repository, open_finance_service=get_open_finance_service())


def run_once() -> bool:
    job = build_worker().run_once()
    if not job:
        print("No queued jobs.")
        return False
    print(f"Processed job {job.id} with status {job.status}.")
    return True


def run_loop(poll_interval: float) -> None:
    worker = build_worker()
    while True:
        job = worker.run_once()
        if job:
            print(f"Processed job {job.id} with status {job.status}.")
            continue
        time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Financy background job worker")
    parser.add_argument("--once", action="store_true", help="Process one queued job and exit.")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Seconds to wait when no jobs are queued.")
    args = parser.parse_args()
    if args.once:
        run_once()
        return
    run_loop(args.poll_interval)


if __name__ == "__main__":
    main()
