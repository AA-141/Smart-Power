"""Core data model: enums and the persisted schedule state."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PowerActionType(str, Enum):
    SHUTDOWN = "shutdown"
    RESTART = "restart"
    SLEEP = "sleep"
    LOCK = "lock"


class ScheduleMode(str, Enum):
    RELATIVE = "relative"
    EXACT = "exact"


class ScheduleStatus(str, Enum):
    ARMED = "armed"
    GRACE_PERIOD = "grace_period"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED_SLEEP = "expired_sleep"
    FAILED = "failed"


_ACTIVE_STATUSES = {ScheduleStatus.ARMED, ScheduleStatus.GRACE_PERIOD}


@dataclass
class ActiveSchedule:
    schedule_id: str
    action: PowerActionType
    mode: ScheduleMode
    target_time_iso: str
    created_at_iso: str
    status: ScheduleStatus
    grace_period_granted: bool = False
    original_target_iso: Optional[str] = None
    worker_pid: Optional[int] = None
    error_message: Optional[str] = None

    @property
    def target_datetime(self) -> datetime:
        return datetime.fromisoformat(self.target_time_iso)

    @property
    def created_datetime(self) -> datetime:
        return datetime.fromisoformat(self.created_at_iso)

    @property
    def is_live(self) -> bool:
        return self.status in _ACTIVE_STATUSES

    def remaining_seconds(self, now: Optional[datetime] = None) -> float:
        ref = now or datetime.now()
        return (self.target_datetime - ref).total_seconds()

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "schedule_id": self.schedule_id,
            "action": self.action.value,
            "mode": self.mode.value,
            "target_time_iso": self.target_time_iso,
            "created_at_iso": self.created_at_iso,
            "status": self.status.value,
            "grace_period_granted": self.grace_period_granted,
            "original_target_iso": self.original_target_iso,
            "worker_pid": self.worker_pid,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ActiveSchedule":
        return cls(
            schedule_id=str(payload["schedule_id"]),
            action=PowerActionType(str(payload["action"])),
            mode=ScheduleMode(str(payload.get("mode", ScheduleMode.RELATIVE.value))),
            target_time_iso=str(payload["target_time_iso"]),
            created_at_iso=str(payload["created_at_iso"]),
            status=ScheduleStatus(str(payload.get("status", ScheduleStatus.ARMED.value))),
            grace_period_granted=bool(payload.get("grace_period_granted", False)),
            original_target_iso=payload.get("original_target_iso"),
            worker_pid=payload.get("worker_pid"),
            error_message=payload.get("error_message"),
        )
