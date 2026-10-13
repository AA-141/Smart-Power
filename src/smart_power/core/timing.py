"""Wall-clock timing helpers for Smart Power schedules."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

_DURATION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([mMhH])?\s*$")
MIN_DURATION_SECONDS = 60
MAX_DURATION_SECONDS = 24 * 60 * 60
# ponytail: fixed 15s overdue threshold, expose as CLI/config option if users demand tuning.
OVERDUE_THRESHOLD_SECONDS = 15.0


def parse_relative_duration(text: str) -> Tuple[bool, str, Optional[float]]:
    """Parse strings such as '25', '25m', '2h' into seconds."""
    match = _DURATION_RE.match(text or "")
    if not match:
        return False, "Enter a duration like 25, 25m, or 2h.", None
    amount = float(match.group(1))
    unit = (match.group(2) or "m").lower()
    seconds = amount * 3600.0 if unit == "h" else amount * 60.0
    if seconds < MIN_DURATION_SECONDS:
        return False, "Duration must be at least 1 minute.", None
    if seconds > MAX_DURATION_SECONDS:
        return False, "Duration must not exceed 24 hours.", None
    return True, "", seconds


def parse_exact_time(text: str, now: Optional[datetime] = None) -> Tuple[bool, str, Optional[datetime]]:
    """Parse local clock input; past times roll forward to tomorrow."""
    now = now or datetime.now()
    normalized = (text or "").strip().lower().replace(".", "")
    formats = ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p")
    parsed_time = None
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(normalized, fmt).time()
            break
        except ValueError:
            continue
    if parsed_time is None:
        return False, "Enter a valid time like 15:30 or 3:30 PM.", None
    target = now.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
    rolled_over = False
    if target <= now:
        target += timedelta(days=1)
        rolled_over = True
    return True, ("Tomorrow" if rolled_over else ""), target


def target_from_duration(seconds: float, now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now()
    return now + timedelta(seconds=seconds)


def remaining_seconds(target: datetime, now: Optional[datetime] = None) -> float:
    now = now or datetime.now()
    return (target - now).total_seconds()


def is_overdue(target: datetime, now: Optional[datetime] = None,
               threshold: float = OVERDUE_THRESHOLD_SECONDS) -> bool:
    return remaining_seconds(target, now) < -threshold


def format_countdown(total_seconds: float) -> str:
    clamped = max(0, int(total_seconds))
    hours, rest = divmod(clamped, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_target(target: datetime) -> str:
    return target.strftime("%A, %B %d, %Y at %I:%M %p")


def format_duration(total_seconds: float) -> str:
    clamped = max(0, int(total_seconds))
    hours, rest = divmod(clamped, 3600)
    minutes, seconds = divmod(rest, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)
