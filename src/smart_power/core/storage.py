"""Atomic state persistence and worker-process liveness checks."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from .models import ActiveSchedule, ScheduleStatus

APP_DIR_NAME = "SmartPower"
STATE_FILE_NAME = "state.json"


def default_state_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIR_NAME / STATE_FILE_NAME
    return Path.home() / f".{APP_DIR_NAME.lower()}" / STATE_FILE_NAME


def load_state(path: Optional[Path] = None) -> Optional[ActiveSchedule]:
    state_path = Path(path) if path else default_state_path()
    try:
        raw = state_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return ActiveSchedule.from_dict(payload)
    except (KeyError, ValueError):
        return None


def save_state(schedule: ActiveSchedule, path: Optional[Path] = None) -> Path:
    state_path = Path(path) if path else default_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(schedule.to_dict(), indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_name, state_path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except OSError:
            pass
    return state_path


def clear_state(path: Optional[Path] = None) -> None:
    state_path = Path(path) if path else default_state_path()
    try:
        state_path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def process_is_running(pid: Optional[int]) -> bool:
    """Best-effort liveness check without depending on third-party packages."""
    if pid is None:
        return False
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid_int)
            if not handle:
                return False
            try:
                code = ctypes.wintypes.DWORD()
                ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
                # ponytail: STILL_ACTIVE (259) only; full creation-time validation if PID reuse bites.
                return bool(ok) and code.value == 259
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            # Conservative fallback: if the state file claims the current process, trust it.
            return pid_int == os.getpid()
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def prune_stale_state(path: Optional[Path] = None) -> Optional[ActiveSchedule]:
    schedule = load_state(path)
    if schedule is None:
        return None
    if schedule.is_live and not process_is_running(schedule.worker_pid):
        schedule.status = ScheduleStatus.CANCELLED
        schedule.error_message = "Schedule expired because the background worker is no longer running."
        clear_state(path)
        return None
    return schedule


if __name__ == "__main__":
    tmp = Path(tempfile.gettempdir()) / "smart-power-selfcheck-state.json"
    from datetime import datetime, timedelta
    from .models import PowerActionType, ScheduleMode
    sample = ActiveSchedule(
        schedule_id="selfcheck",
        action=PowerActionType.LOCK,
        mode=ScheduleMode.RELATIVE,
        target_time_iso=(datetime.now() + timedelta(minutes=5)).isoformat(timespec="seconds"),
        created_at_iso=datetime.now().isoformat(timespec="seconds"),
        status=ScheduleStatus.ARMED,
        worker_pid=os.getpid(),
    )
    save_state(sample, tmp)
    assert load_state(tmp) is not None
    assert process_is_running(os.getpid())
    assert not process_is_running(-42)
    clear_state(tmp)
    assert load_state(tmp) is None
    print("storage self-check passed")
