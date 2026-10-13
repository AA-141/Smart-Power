"""Headless background worker: waits for target time and executes once."""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
try:
    from src.smart_power.actions import registry  # noqa: E402
    from src.smart_power.core import storage, timing  # noqa: E402
    from src.smart_power.core.models import ScheduleStatus  # noqa: E402
except ImportError:
    from smart_power.actions import registry  # noqa: E402
    from smart_power.core import storage, timing  # noqa: E402
    from smart_power.core.models import ScheduleStatus  # noqa: E402

GRACE_SECONDS = 120.0
POLL_SECONDS = 1.0


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Smart Power background worker")
    parser.add_argument("--schedule-id", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--mode", default="relative")
    return parser.parse_args(argv)


def execute_action(action_id: str, force: bool, dry_run: bool = False):
    action = registry.get(action_id)
    return action.execute(force=force, dry_run=dry_run)


def worker_main(argv=None) -> int:
    args = _parse_args(argv)
    schedule = storage.load_state()
    if schedule is None or schedule.schedule_id != args.schedule_id:
        return 2
    schedule.worker_pid = os.getpid()
    storage.save_state(schedule)

    while True:
        schedule = storage.load_state()
        if schedule is None or schedule.schedule_id != args.schedule_id:
            return 0
        if not schedule.is_live:
            return 0
        now = datetime.now()
        remaining = schedule.remaining_seconds(now)
        if remaining > 0:
            time.sleep(min(POLL_SECONDS, remaining))
            continue
        if timing.is_overdue(schedule.target_datetime, now):
            schedule.status = ScheduleStatus.EXPIRED_SLEEP
            schedule.error_message = "Cancelled because the system woke up after the scheduled time."
            storage.save_state(schedule)
            return 3
        action = registry.get(schedule.action.value)
        dry_run = os.environ.get("SMART_POWER_DRY_RUN") == "1"
        if not action.is_destructive:
            result = action.execute(force=False, dry_run=dry_run)
            schedule.status = ScheduleStatus.COMPLETED if result.success else ScheduleStatus.FAILED
            schedule.error_message = None if result.success else result.message
            storage.save_state(schedule)
            return 0 if result.success else 4
        if not schedule.grace_period_granted:
            first = action.execute(force=False, dry_run=dry_run)
            if first.success and not dry_run:
                schedule.status = ScheduleStatus.COMPLETED
                storage.save_state(schedule)
                return 0
            if dry_run:
                schedule.status = ScheduleStatus.COMPLETED
                storage.save_state(schedule)
                return 0
            # Blocked (or ambiguous failure): grant one conditional extension.
            schedule.grace_period_granted = True
            schedule.original_target_iso = schedule.original_target_iso or schedule.target_time_iso
            schedule.target_time_iso = (schedule.target_datetime + timedelta(seconds=GRACE_SECONDS)).isoformat(timespec="seconds")
            schedule.status = ScheduleStatus.GRACE_PERIOD
            schedule.error_message = "Blocked by running applications. 2-minute grace period granted."
            storage.save_state(schedule)
            continue
        forced = action.execute(force=True, dry_run=dry_run)
        schedule.status = ScheduleStatus.COMPLETED if forced.success else ScheduleStatus.FAILED
        schedule.error_message = None if forced.success else forced.message
        storage.save_state(schedule)
        return 0 if forced.success else 5


if __name__ == "__main__":
    raise SystemExit(worker_main())
