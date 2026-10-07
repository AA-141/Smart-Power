# Research & Technical Decisions: Smart Power TUI

**Feature**: `001-tui-power-scheduler`  
**Phase**: Phase 0 (Technical Investigation & Decision Matrix)  
**Date**: 2026-09-30

---

## 1. TUI Framework & Styling

### Options Evaluated
1. **Textual**: Modern asynchronous Python TUI framework with reactive widgets.
   - *Pros*: Built-in widgets (buttons, input fields), reactive UI state.
   - *Cons*: Heavy dependency tree; async event loop (`asyncio`) adds event loop complexity when spawning/managing detached Windows background processes; higher idle memory (~35-50 MB).
2. **Prompt Toolkit (`prompt_toolkit`)**: Low-level terminal library.
   - *Pros*: Excellent for text input prompts; already installed in the environment.
   - *Cons*: Complex layout DSL for full-screen dashboards; steeper learning curve for box-drawing and countdown panels.
3. **Rich (`rich`) + Standard Library `msvcrt`**:
   - *Pros*: `rich` 14.3.3 is already installed; lightweight (<15 MB); world-class rendering for panels, tables, ANSI 16-color & truecolor palette, live updating (`rich.live.Live`); `msvcrt` is built into Python on Windows for non-blocking keyboard input (`msvcrt.kbhit()`, `msvcrt.getch()`).
   - *Cons*: Manual key event loop, but for a 3-step wizard and 1 status screen, the entire navigation loop is fewer than 150 lines of clear, maintainable code.

### Decision
**Rich + `msvcrt` keyboard navigation loop**.
- **Visuals**: Primary black background (`#000000`), deep/cyan blue borders, pure white typography, subtle purple titles/badges, and orange warnings/alerts.
- **Why**: Zero additional dependencies installed (reuses existing `rich`), deterministic synchronous flow, rock-solid keyboard navigation on Windows Terminal and conhost, instant responsiveness, and zero async complexity.

---

## 2. Background Scheduling & Process Lifecycle

### Options Evaluated
1. **Windows Task Scheduler (`schtasks.exe`)**:
   - *Pros*: Runs without keeping Python alive.
   - *Cons*: Clunky CLI interface; granular sub-minute updates or dynamic 2-minute grace extensions require fragile XML task definitions; difficult to inspect live countdown from another process; leaves orphaned tasks if corrupted.
2. **Windows Service (`pywin32` / `sc.exe`)**:
   - *Pros*: High survivability.
   - *Cons*: Requires Administrator privileges to register/install; violates zero-install/portable requirement; over-engineered (YAGNI).
3. **Detached Headless Python Worker Process**:
   - *Implementation*: Main TUI spawns worker via `subprocess.Popen([sys.executable, "-m", "smart_power.worker", ...], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)`.
   - *Pros*:
     - Standard user rights (no admin required to schedule).
     - Headless (no console window flashes or remains on screen).
     - Persists after TUI closes; updates `%LOCALAPPDATA%\SmartPower\state.json`.
     - Re-attaching TUI reads `state.json` and verifies worker PID via `psutil.pid_exists(pid)`.
     - In event of reboot, worker PID disappears; next launch cleanly expires the schedule.
   - *Cons*: Consumes ~12-15 MB RAM while running. Meets the < 25 MB budget easily.

### Decision
**Detached Headless Python Worker Process** with Windows `DETACHED_PROCESS` flag and state synchronization via user-isolated JSON file.

---

## 3. Windows Native Power Operations

### Technical Approaches
- **Shutdown**:
  - Normal/Extended: `shutdown.exe /s /t 0`
  - Forced (after 2-min grace): `shutdown.exe /s /f /t 0`
- **Restart**:
  - Normal/Extended: `shutdown.exe /r /t 0`
  - Forced (after 2-min grace): `shutdown.exe /r /f /t 0`
- **Sleep (Standby)**:
  - Standard Win32 API via `ctypes.windll.powrprof.SetSuspendState(0, 1, 0)`.
  - Fallback / CLI equivalent: `rundll32.exe powrprof.dll,SetSuspendState 0,1,0`.
- **Lock Session**:
  - Standard Win32 API: `ctypes.windll.user32.LockWorkStation()`.
  - Instant, requires 0 elevation, completely safe.
- **Abort Pending Shutdown/Restart**:
  - `shutdown.exe /a`.

### Decision
Centralized `PowerExecutor` module providing abstract `is_supported()`, `execute(force=False)`, and `abort()`. Standardizes subprocess calls with argument lists (never raw shell strings).

---

## 4. Scheduling & Time Drift / Wake Handling

### Principles
1. **Wall-Clock Reference**: Always compute `remaining_seconds = (target_datetime - datetime.now()).total_seconds()`. Never rely on tick counting (`remaining -= 1`).
2. **Overdue Wake-up Detection**:
   - If the system suspends/sleeps during a countdown and wakes up after `target_datetime`, the time delta becomes negative by more than a brief jitter threshold (>15s).
   - The worker detects this, marks state as `EXPIRED_SLEEP`, aborts power execution, and registers an English explanation.
3. **Conditional 2-Minute Extension Execution Policy**:
   - When remaining seconds reach $\le 0$, if target action is destructive (Shutdown/Restart):
     - An initial standard execution (`force=False`) is attempted so Windows gives running applications a chance to close gracefully.
     - If Windows executes the shutdown, the system shuts down normally with zero delay.
     - If Windows blocks the shutdown (e.g. applications with unsaved files refuse to exit), the worker detects the block, issues an urgent alert/chime, grants +120s extension, and marks `grace_period_granted = True`.
     - Once the 120s grace period expires, the worker re-attempts execution with `force=True` (`/f`), guaranteeing that the shutdown or restart proceeds deterministically.

---

## 5. Persistence & State Storage

### Approach
- **Location**: `%LOCALAPPDATA%\SmartPower\state.json` (with fallback to `~/.smart_power/state.json`).
- **Atomic Writes**: Write to temporary file in the same directory, then `os.replace` to guarantee zero half-written reads.
- **Single Active Schedule Enforcement**: State file maintains an `ACTIVE` status token and the worker PID. If active, new schedule creation is blocked until cancelled or finished.

---

## 6. Testing & Simulation Strategy

- **Mock Execution Mode**: Environment variable `SMART_POWER_DRY_RUN=1` or parameter `dry_run=True` in `PowerExecutor`.
- **Unit Tests**: Full unit test coverage for:
  - Time calculation (exact rollover, relative conversion).
  - 2-minute extension state machine.
  - Overdue sleep detection.
  - JSON state serialization / corrupted file recovery.
- Runs with stdlib `unittest` in < 2 seconds.
