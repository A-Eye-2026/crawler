"""
scripts/run_all_collectors.py

자동 수집 스케줄러 실행 파일

역할:
- APScheduler로 collector를 주기 실행
- 파일 잠금으로 중복 실행을 방지
- 로컬 개발용 수동 실행 스크립트는 그대로 유지
"""

import os
import time
from contextlib import contextmanager
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import (
    BASE_DIR,
    DISASTER_COLLECTION_INTERVAL_MINUTES,
    WILDFIRE_COLLECTION_INTERVAL_MINUTES,
)
from app.collectors.disaster_message_collector import DisasterMessageCollector
from app.collectors.wildfire_risk_collector import WildfireRiskCollector


LOCK_DIR = BASE_DIR / "storage" / "locks"
LOCK_STALE_SECONDS = 60 * 60 * 2  # 비정상 종료 뒤 잠금이 영구히 남지 않도록 2시간 뒤 재획득 허용


def ensure_lock_dir():
    """
    잠금 파일 보관 폴더를 준비한다.
    """
    LOCK_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def collector_lock(lock_name):
    """
    같은 collector가 겹쳐 돌지 않도록 파일 잠금을 건다.
    """
    ensure_lock_dir()
    lock_path = LOCK_DIR / f"{lock_name}.lock"
    lock_fd = None

    try:
        if lock_path.exists():
            lock_age = time.time() - lock_path.stat().st_mtime

            # 비정상 종료로 남은 오래된 lock은 새 실행이 회복할 수 있게 제거한다.
            if lock_age > LOCK_STALE_SECONDS:
                lock_path.unlink(missing_ok=True)

        lock_fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        yield True

    except FileExistsError:
        print(f"[SKIP] {lock_name} already running; overlapping execution prevented.")
        yield False

    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            lock_path.unlink(missing_ok=True)


def run_disaster_collector_job():
    """
    재난문자 collector 스케줄 작업
    """
    with collector_lock("disaster_message_collector") as acquired:
        if not acquired:
            return

        DisasterMessageCollector().collect()


def run_wildfire_collector_job():
    """
    산불위험예보 collector 스케줄 작업
    """
    with collector_lock("wildfire_risk_collector") as acquired:
        if not acquired:
            return

        WildfireRiskCollector().collect()


def main():
    """
    APScheduler 기반 자동 수집 스케줄러 시작
    """
    scheduler = BlockingScheduler(
        job_defaults={
            "coalesce": True,  # 지연된 실행이 쌓이면 최신 한 번으로 합쳐 과도한 연속 실행을 막는다.
            "max_instances": 1,  # 같은 job이 scheduler 내부에서 동시에 두 번 돌지 않게 한다.
            "misfire_grace_time": 300,
        }
    )

    scheduler.add_job(
        run_disaster_collector_job,
        trigger=IntervalTrigger(minutes=DISASTER_COLLECTION_INTERVAL_MINUTES),
        id="disaster_message_collector_job",
        name="Disaster Message Collector",
        replace_existing=True,
    )

    scheduler.add_job(
        run_wildfire_collector_job,
        trigger=IntervalTrigger(minutes=WILDFIRE_COLLECTION_INTERVAL_MINUTES),
        id="wildfire_risk_collector_job",
        name="Wildfire Risk Collector",
        replace_existing=True,
    )

    print(
        "[START] Collector scheduler started "
        f"(disaster={DISASTER_COLLECTION_INTERVAL_MINUTES}m, "
        f"wildfire={WILDFIRE_COLLECTION_INTERVAL_MINUTES}m)"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[END] Collector scheduler stopped.")


if __name__ == "__main__":
    main()
