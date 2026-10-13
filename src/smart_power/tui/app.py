"""Interactive TUI controller with synchronous Windows keyboard input."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.live import Live

from ..actions import registry
from ..actions.base import PowerActionHandler
from ..core import storage, timing
from ..core.models import ActiveSchedule, PowerActionType, ScheduleMode, ScheduleStatus
from . import views

try:
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows fallback for tests
    msvcrt = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_key(timeout: float = 0.1) -> str:
    if msvcrt is None:
        time.sleep(timeout)
        return ""
    end = time.time() + timeout
    while time.time() < end:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                extra = msvcrt.getwch()
                mapping = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}
                return mapping.get(extra, "")
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch == "\x1b":
                return "ESC"
            return ch
        time.sleep(0.02)
    return ""


class SmartPowerApp:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.actions: List[PowerActionHandler] = registry.all_actions()

    def run(self) -> int:
        try:
            existing = storage.prune_stale_state()
            if existing is not None and existing.is_live:
                return self.active_loop(existing)
            return self.wizard()
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            self.console.print(views.error_panel(f"Unexpected error: {exc}"))
            self.console.print("[dim]Press any key to exit.[/dim]")
            _read_key(timeout=30)
            return 1

    def wizard(self) -> int:
        mode_index = 0
        while True:
            self.console.clear()
            self.console.print(views.main_menu(mode_index))
            key = _read_key(timeout=30)
            if key in ("q", "Q", "ESC"):
                return 0
            if key == "UP":
                mode_index = (mode_index - 1) % 3
            elif key == "DOWN":
                mode_index = (mode_index + 1) % 3
            elif key == "ENTER":
                if mode_index == 2:
                    return 0
                target = self._ask_time(mode_index)
                if target is None:
                    continue
                action = self._ask_action()
                if action is None:
                    continue
                return self._confirm_and_arm(action, target,
                                             ScheduleMode.RELATIVE if mode_index == 0 else ScheduleMode.EXACT)

    def _ask_time(self, mode_index: int) -> Optional[datetime]:
        text, error = "", ""
        relative = mode_index == 0
        title = "RELATIVE DURATION" if relative else "EXACT CLOCK TIME"
        prompt = "Duration (minutes/hours):" if relative else "Clock time:"
        example = "25, 25m, 2h" if relative else "15:30 or 3:30 PM"
        while True:
            self.console.clear()
            self.console.print(views.text_input(title, prompt, text, error, example))
            key = _read_key(timeout=60)
            if key == "ESC":
                return None
            if key == "ENTER":
                if relative:
                    ok, message, seconds = timing.parse_relative_duration(text)
                    if not ok:
                        error = message
                        continue
                    return timing.target_from_duration(seconds or 0)
                ok, extra, target = timing.parse_exact_time(text)
                if not ok:
                    error = extra
                    continue
                if extra:
                    self.console.clear()
                    self.console.print(views.info_panel("ROLLOVER", [f"Scheduled for tomorrow ({target})."]))
                    _read_key(timeout=2)
                return target
            if key in ("UP", "DOWN", ""):
                continue
            if key == "\x08":
                text = text[:-1]
            elif len(key) == 1 and len(text) < 24:
                text += key
                error = ""

    def _ask_action(self) -> Optional[PowerActionHandler]:
        index = 0
        while True:
            self.console.clear()
            self.console.print(views.action_menu(self.actions, index))
            key = _read_key(timeout=60)
            if key == "ESC":
                return None
            if key == "UP":
                index = (index - 1) % len(self.actions)
            elif key == "DOWN":
                index = (index + 1) % len(self.actions)
            elif key == "ENTER":
                return self.actions[index]

    def _confirm_and_arm(self, action: PowerActionHandler, target: datetime, mode: ScheduleMode) -> int:
        seconds = max(0.0, (target - datetime.now()).total_seconds())
        while True:
            self.console.clear()
            self.console.print(views.review_panel(action, target, seconds))
            key = _read_key(timeout=120)
            if key in ("n", "N", "ESC"):
                return 0
            if key in ("ENTER", "y", "Y"):
                schedule = ActiveSchedule(
                    schedule_id=f"sp-{uuid.uuid4().hex[:8]}",
                    action=PowerActionType(action.action_id),
                    mode=mode,
                    target_time_iso=target.isoformat(timespec="seconds"),
                    created_at_iso=datetime.now().isoformat(timespec="seconds"),
                    status=ScheduleStatus.ARMED,
                )
                storage.save_state(schedule)
                self.spawn_worker(schedule)
                stored = storage.load_state()
                return self.active_loop(stored or schedule)

    def spawn_worker(self, schedule: ActiveSchedule) -> None:
        cmd = [sys.executable, "-m", "smart_power.worker",
               "--schedule-id", schedule.schedule_id,
               "--action", schedule.action.value,
               "--target", schedule.target_time_iso,
               "--mode", schedule.mode.value]
        kwargs = {"cwd": str(_project_root())}
        env = dict(os.environ)
        src_dir = str(_project_root() / "src")
        if env.get("PYTHONPATH"):
            env["PYTHONPATH"] = src_dir + os.pathsep + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = src_dir
        kwargs["env"] = env
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NO_WINDOW", 0)
        else:
            kwargs["start_new_session"] = True
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
        try:
            proc = subprocess.Popen(cmd, **kwargs)
            schedule.worker_pid = proc.pid
            storage.save_state(schedule)
        except Exception as exc:
            storage.clear_state()
            self.console.clear()
            self.console.print(views.error_panel(f"Could not start background worker: {exc}"))
            _read_key(timeout=10)

    def active_loop(self, schedule: ActiveSchedule) -> int:
        confirm_cancel = False
        with Live(views.countdown_panel(schedule, self.actions), console=self.console,
                  refresh_per_second=1, screen=False) as live:
            while True:
                current = storage.load_state()
                if current is None or current.schedule_id != schedule.schedule_id:
                    self.console.clear()
                    self.console.print(views.info_panel("SCHEDULE ENDED", ["No active schedule remains."]))
                    _read_key(timeout=5)
                    return 0
                if not current.is_live:
                    self.console.clear()
                    detail = current.error_message or f"Final status: {current.status.value}."
                    self.console.print(views.info_panel("SCHEDULE FINISHED", [detail]))
                    storage.clear_state()
                    _read_key(timeout=8)
                    return 0
                live.update(views.countdown_panel(current, self.actions))
                key = _read_key(timeout=0.25)
                if not key:
                    continue
                key_up = key.upper() if len(key) == 1 else key
                if key_up == "Q":
                    return 0
                if confirm_cancel:
                    if key_up in ("Y", "ENTER"):
                        self.cancel_schedule(current)
                        return 0
                    confirm_cancel = False
                    continue
                if key_up in ("C", "ESC"):
                    live.stop()
                    self.console.clear()
                    self.console.print(views.confirm_panel(
                        "CANCEL SCHEDULE",
                        f"Cancel the scheduled {current.action.value}?"))
                    nested = _read_key(timeout=30)
                    nested_up = nested.upper() if len(nested) == 1 else nested
                    if nested_up in ("Y", "ENTER"):
                        self.cancel_schedule(current)
                        return 0
                    return self.active_loop(current)

    def cancel_schedule(self, schedule: ActiveSchedule) -> None:
        try:
            action = registry.get(schedule.action.value)
            action.abort(dry_run=False)
        except Exception:
            pass
        pid = schedule.worker_pid
        if pid and pid != os.getpid():
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                   capture_output=True, timeout=10)
                else:
                    os.kill(int(pid), 15)
            except Exception:
                pass
        storage.clear_state()
        self.console.clear()
        self.console.print(views.info_panel("CANCELLED", ["Schedule cancelled successfully."]))
        _read_key(timeout=4)


def run() -> int:
    return SmartPowerApp().run()
