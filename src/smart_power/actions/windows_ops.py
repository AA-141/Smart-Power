"""Windows-native power operations with safe dry-run behavior."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .base import ActionResult

SHUTDOWN_EXE = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "shutdown.exe")


def dry_run_enabled(explicit: bool = False) -> bool:
    return explicit or os.environ.get("SMART_POWER_DRY_RUN") == "1"


def _run(argv: list[str], dry_run: bool, what: str) -> ActionResult:
    if dry_run_enabled(dry_run):
        return ActionResult(True, f"DRY RUN: {' '.join(argv)}")
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    except FileNotFoundError as exc:
        return ActionResult(False, f"{what} failed: executable not found ({exc}).")
    except subprocess.TimeoutExpired:
        return ActionResult(False, f"{what} timed out before Windows responded.")
    except OSError as exc:
        return ActionResult(False, f"{what} failed to start: {exc}.")
    output = (completed.stdout or "") + (completed.stderr or "")
    lowered = output.lower()
    blocked_markers = (
        "preventing",
        "this app is preventing",
        "unsaved",
        "are preventing",
        "cannot be performed",
        "operation did not complete",
    )
    if completed.returncode == 0:
        return ActionResult(True, f"{what} command accepted by Windows.")
    blocked = any(marker in lowered for marker in blocked_markers)
    detail = output.strip() or f"exit code {completed.returncode}"
    if blocked:
        return ActionResult(False, f"{what} was blocked by Windows: {detail}", blocked=True)
    return ActionResult(False, f"{what} failed: {detail}")


def _enable_shutdown_privilege() -> None:
    """Best-effort enable of SeShutdownPrivilege for interactive users."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        TOKEN_ADJUST_PRIVILEGES = 0x20
        TOKEN_QUERY = 0x8
        SE_PRIVILEGE_ENABLED = 0x2

        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", wintypes.DWORD),
                        ("Privileges", LUID * 1),
                        ("Attributes", wintypes.DWORD * 1)]

        token = wintypes.HANDLE()
        process = kernel32.GetCurrentProcess()
        if not advapi32.OpenProcessToken(process, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)):
            return
        try:
            luid = LUID()
            if not advapi32.LookupPrivilegeValueW(None, "SeShutdownPrivilege", ctypes.byref(luid)):
                return
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0] = luid
            tp.Attributes[0] = SE_PRIVILEGE_ENABLED
            advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)
        finally:
            kernel32.CloseHandle(token)
    except Exception:
        pass


def shutdown_command(force: bool) -> list[str]:
    argv = [SHUTDOWN_EXE, "/s", "/t", "0"]
    if force:
        argv.insert(2, "/f")
    return argv


def restart_command(force: bool) -> list[str]:
    argv = [SHUTDOWN_EXE, "/r", "/t", "0"]
    if force:
        argv.insert(2, "/f")
    return argv


def abort_command() -> list[str]:
    return [SHUTDOWN_EXE, "/a"]


@dataclass
class _ShutdownAction:
    action_id: str = "shutdown"
    display_name: str = "Shutdown System"
    description: str = "Power off this PC completely."
    is_destructive: bool = True

    def is_supported(self):
        return True, ""

    def execute(self, force: bool = False, dry_run: bool = False) -> ActionResult:
        _enable_shutdown_privilege()
        return _run(shutdown_command(force), dry_run, "Shutdown")

    def abort(self, dry_run: bool = False) -> ActionResult:
        return _run(abort_command(), dry_run, "Shutdown abort")


@dataclass
class _RestartAction:
    action_id: str = "restart"
    display_name: str = "Restart System"
    description: str = "Reboot this PC."
    is_destructive: bool = True

    def is_supported(self):
        return True, ""

    def execute(self, force: bool = False, dry_run: bool = False) -> ActionResult:
        _enable_shutdown_privilege()
        return _run(restart_command(force), dry_run, "Restart")

    def abort(self, dry_run: bool = False) -> ActionResult:
        return _run(abort_command(), dry_run, "Restart abort")


@dataclass
class _SleepAction:
    action_id: str = "sleep"
    display_name: str = "Sleep"
    description: str = "Put this PC into standby."
    is_destructive: bool = False

    def is_supported(self):
        return True, ""

    def execute(self, force: bool = False, dry_run: bool = False) -> ActionResult:
        if dry_run_enabled(dry_run):
            return ActionResult(True, "DRY RUN: SetSuspendState(0, 1, 0)")
        if os.name != "nt":
            return ActionResult(False, "Sleep is supported only on Windows.")
        try:
            import ctypes
            ok = ctypes.windll.powrprof.SetSuspendState(False, True, False)
        except Exception as exc:
            return ActionResult(False, f"Sleep request failed: {exc}.")
        if not ok:
            return ActionResult(False, "Windows declined the sleep request.")
        return ActionResult(True, "Sleep command accepted by Windows.")

    def abort(self, dry_run: bool = False) -> ActionResult:
        return ActionResult(True, "Sleep has no pending timer to abort.")


@dataclass
class _LockAction:
    action_id: str = "lock"
    display_name: str = "Lock Session"
    description: str = "Lock the current Windows session."
    is_destructive: bool = False

    def is_supported(self):
        return True, ""

    def execute(self, force: bool = False, dry_run: bool = False) -> ActionResult:
        if dry_run_enabled(dry_run):
            return ActionResult(True, "DRY RUN: LockWorkStation()")
        if os.name != "nt":
            return ActionResult(False, "Lock is supported only on Windows.")
        try:
            import ctypes
            ok = ctypes.windll.user32.LockWorkStation()
        except Exception as exc:
            return ActionResult(False, f"Lock request failed: {exc}.")
        if not ok:
            return ActionResult(False, "Windows declined the lock request.")
        return ActionResult(True, "Workstation locked.")

    def abort(self, dry_run: bool = False) -> ActionResult:
        return ActionResult(True, "Lock executes immediately; nothing to abort.")


SHUTDOWN_ACTION = _ShutdownAction()
RESTART_ACTION = _RestartAction()
SLEEP_ACTION = _SleepAction()
LOCK_ACTION = _LockAction()

if __name__ == "__main__":
    for action in (SHUTDOWN_ACTION, RESTART_ACTION, SLEEP_ACTION, LOCK_ACTION):
        result = action.execute(dry_run=True)
        assert result.success, action.action_id
    assert abort_command() == [SHUTDOWN_EXE, "/a"]
    assert shutdown_command(True)[2] == "/f"
    assert restart_command(True)[2] == "/f"
    print("windows_ops self-check passed")
