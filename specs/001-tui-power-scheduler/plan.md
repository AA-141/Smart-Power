# Implementation Plan: Interactive TUI Power Action Scheduler

**Branch**: `001-tui-power-scheduler` | **Date**: 2026-09-30 | **Spec**: [specs/001-tui-power-scheduler/spec.md](spec.md)

**Input**: Feature specification from `/specs/001-tui-power-scheduler/spec.md`

## Summary

Smart Power is a Windows-first desktop utility featuring a polished, interactive Terminal User Interface (TUI) for scheduling system power actions (Shutdown, Restart, Sleep, Lock). The architecture couples an interactive TUI (using `rich` for layout/styling and `msvcrt` for responsive keyboard navigation) with a detached headless Python background worker process. The worker independently executes the target operation and persists state via `%LOCALAPPDATA%\SmartPower\state.json`, ensuring the schedule continues reliably even if the visible TUI window is closed. Destructive actions follow a conditional 2-minute extension policy: non-force execution is attempted at target time, and if blocked by unsaved applications, a 120-second grace period is granted before re-attempting with force.

---

## Technical Context

**Language/Version**: Python 3.10+ (targeted and tested on Python 3.11.15 on Windows 11)  
**Primary Dependencies**: `rich` (v14.3.3, already installed in environment), standard library `msvcrt`, `subprocess`, `ctypes`, `threading`, `json`, `psutil` (v7.2.2, already installed for process health checks)  
**Storage**: Atomic JSON persistence at `%LOCALAPPDATA%\SmartPower\state.json` (fallback `~/.smart_power/state.json`)  
**Testing**: Python standard library `unittest` (`test_timing.py`, `test_actions.py`, `test_storage.py`, `test_worker.py`)  
**Target Platform**: Microsoft Windows 10 (1903+) / Windows 11 (Windows Terminal & ConHost with ANSI support)  
**Project Type**: Desktop CLI / Interactive TUI utility  
**Performance Goals**: Idle background worker RAM < 15 MB, CPU < 0.1%; TUI input latency < 16ms; countdown refresh rate 1 Hz  
**Constraints**: Single active schedule policy; 100% English UI; zero unhandled crash traces; safe mock dry-run mode for tests  
**Scale/Scope**: Single-user desktop utility, 4 primary actions, modular extensible action registry  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- [x] **I. Windows-First Python Implementation**: Utilizes native Windows facilities (`shutdown.exe`, `Powrprof.dll`, `user32.dll`) via stdlib `subprocess` and `ctypes`.
- [x] **II. Strict Separation of Concerns**: TUI views (`tui/`), core application logic (`core/`), power execution (`actions/`), background execution (`worker.py`), and storage (`core/storage.py`) are strictly decoupled.
- [x] **III. Pragmatic Simplicity (Anti-Over-Engineering)**: Zero unnecessary abstractions or frameworks; direct synchronous keyboard loop and simple worker process.
- [x] **IV. Dependency Economy**: Leverages Python stdlib and already-installed `rich` and `psutil`. No new dependencies introduced.
- [x] **V. Operational Safety & Resilience**: 2-step confirmation for scheduling and cancellation; 2-minute grace period alert for destructive actions; atomic file persistence.
- [x] **VI. Resource Efficiency**: Non-blocking sleep synchronization in worker; idle resource usage well below limits (< 15 MB).
- [x] **VII. Testability & Incremental Evolution**: Actions interface supports mock dry-run execution; modular registry enables adding future actions without rewrites.
- [x] **VIII. English UI & Diagnostics**: 100% English user-facing text, error messages, and structured log formatting.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-tui-power-scheduler/
├── spec.md              # Clarified feature specification
├── plan.md              # This architecture & implementation plan
├── research.md          # Phase 0: Technical decisions and trade-offs
├── data-model.md        # Phase 1: Data models, enums, state machine
├── quickstart.md        # Phase 1: Running, navigation, and testing guide
└── contracts/
    └── actions-api.md   # Phase 1: Action protocol and worker CLI contract
```

### Source Code (repository root)

```text
src/
└── smart_power/
    ├── __init__.py              # Package marker & version info
    ├── __main__.py              # Entry point dispatcher (python -m smart_power)
    ├── main.py                  # CLI argument parsing and mode selector
    ├── worker.py                # Headless background scheduler worker
    ├── core/
    │   ├── __init__.py
    │   ├── models.py            # Enums & ActiveSchedule dataclass
    │   ├── timing.py            # Clock math, relative/exact parser, sleep-wake check
    │   └── storage.py           # Atomic JSON state persistence & process checks
    ├── actions/
    │   ├── __init__.py
    │   ├── base.py              # PowerActionHandler protocol & result dataclass
    │   ├── registry.py          # Action registry (Shutdown, Restart, Sleep, Lock)
    │   └── windows_ops.py       # Windows API & CLI executor (subprocess/ctypes)
    └── tui/
        ├── __init__.py
        ├── theme.py             # Colors (black, blue, white, purple, orange), borders
        ├── views.py             # UI view renderers (Wizard, Confirm, Countdown, Modal)
        └── app.py               # Interactive keyboard event loop controller

tests/
├── __init__.py
├── test_timing.py               # Relative & exact time parsing, rollover, overdue checks
├── test_storage.py              # State serialization, atomic write, corruption fallback
├── test_actions.py              # Mock command generation and action execution
└── test_worker_flow.py          # Worker loop simulation and grace period transitions
```

**Structure Decision**: Single modular Python package under `src/smart_power` with clean separation between UI, Core logic, and OS Actions.

---

## Component Responsibilities

| Module | Responsibility | Key Interactions |
|---|---|---|
| `core.models` | Defines immutable enums and `ActiveSchedule` state dataclass. | Used by all modules. |
| `core.timing` | Converts relative inputs (e.g., "25m") and exact inputs (e.g., "15:00") into local target `datetime`. Detects next-day rollover and overdue sleep-wake states. | Called by TUI and Worker. |
| `core.storage` | Reads, writes, and clears `%LOCALAPPDATA%\SmartPower\state.json` atomically using temporary files. Verifies if worker process is active using PID checks. | Interfaced by TUI and Worker. |
| `actions.windows_ops` | Direct platform executor invoking `shutdown.exe`, `user32.LockWorkStation`, and `powrprof.SetSuspendState`. Honors `dry_run` flag. | Registered into `actions.registry`. |
| `actions.registry` | Manages list of supported actions, descriptions, elevation checks, and execution delegates. | Queried by TUI menus and Worker execution. |
| `worker.py` | Standalone script launched with `DETACHED_PROCESS`. Runs a non-blocking countdown loop (`time.sleep`), checks for cancellation/sleep-wake, grants 2-minute grace if needed, and triggers the action. | Writes status updates to `storage`. |
| `tui.theme` | Centralizes visual tokens: pure black background (`#000000`), cyan/deep blue borders, white primary text, purple headers, and orange warning banners. | Used by `views.py`. |
| `tui.views` | Pure rendering functions returning `rich.panel.Panel` and `rich.layout.Layout` instances for: 1. Mode select, 2. Time input, 3. Action select, 4. Confirmation modal, 5. Active countdown, 6. Cancel modal. | Driven by `app.py`. |
| `tui.app` | Main interactive controller using `msvcrt.getch()` to handle keyboard input, manage screen transitions, spawn the background worker upon confirmation, and re-attach to active schedules. | Orchestrates TUI and Worker handoff. |

---

## Data & Persistence Flow

1. **Launch**: TUI queries `storage.load_state()`.
   - If an `ARMED` or `GRACE_PERIOD` schedule exists and its `worker_pid` is actively running, TUI enters **Active Countdown View** immediately.
   - If state exists but PID is dead (e.g., machine restarted), state is marked `EXPIRED_REBOOT` and cleared; TUI opens **Setup Wizard**.
2. **Scheduling**: User inputs time and selects action $\to$ Review screen renders $\to$ User hits Enter/Confirm $\to$ TUI generates UUID, writes initial `state.json`, and spawns `python -m smart_power.worker` as a detached headless process $\to$ TUI transitions to live countdown.
3. **Closing TUI**: User presses `q` or closes terminal window $\to$ TUI exits cleanly. Detached worker process continues running uninterrupted.
4. **Execution / Grace Period**:
   - Worker reaches $T_{target}$. If action is destructive (Shutdown/Restart):
     - An initial standard execution (`force=False`) is performed.
     - If successful and not blocked, Windows proceeds with shutdown/restart immediately.
     - If Windows blocks the shutdown (due to open unsaved files or applications needing interaction), worker triggers the 2-minute grace period (`grace_period_granted = True`, `target_time += 120s`), emits warning alert/notification, and updates state.
     - When the 120-second grace period expires, worker invokes `action.execute(force=True)` to deterministically shut down or restart the system.
5. **Cancellation**: User presses `c` in TUI $\to$ Cancel confirmation modal appears $\to$ User confirms (`y`) $\to$ Worker PID is terminated, OS abort command (`shutdown /a`) is sent, and `state.json` is cleared.

---

## Testing & Validation Strategy

1. **Unit Tests (stdlib `unittest`)**:
   - `test_timing.py`: Verify relative minutes/hours conversion; verify exact time parsing; verify past-time rolls over to next day (+24h); verify overdue sleep condition when clock jumps forward.
   - `test_storage.py`: Verify atomic JSON save and read; verify handling of corrupt/empty state file; verify PID validation logic.
   - `test_actions.py`: Verify Windows commands constructed for Shutdown (`/s`), Restart (`/r`), Force mode (`/f`), Abort (`/a`), and Lock; verify dry-run simulation mode does not invoke OS calls.
   - `test_worker_flow.py`: Verify simulated countdown transitions from `ARMED` to `GRACE_PERIOD` (+120s) and finally to `COMPLETED`.
2. **Manual & Interactive Verification**:
   - Verify keyboard navigation (Arrow keys, Enter, Esc, C, Q) and color harmony in Windows Terminal.
   - Verify detached execution: schedule a 2-minute Lock action, close the terminal window completely, observe that Windows locks after 2 minutes.
   - Verify re-attach: schedule a 3-minute action, close terminal, reopen after 1 minute, confirm countdown shows ~2 minutes remaining.

---

## Complexity Tracking

> Zero constitution violations. Architecture adheres strictly to simplicity:
- No heavy async loop frameworks used; simple synchronous event loop with standard Windows `msvcrt`.
- No database or external server; plain atomic JSON file.
- No Windows Service or Task Scheduler installation required; zero-install headless background process.

---

## Implementation Phases

- **Phase 1: Core Foundation & Data Layer**
  - Implement `core.models`, `core.timing`, `core.storage`.
  - Write unit tests for timing and storage.
- **Phase 2: Power Action Engine & Windows Integration**
  - Implement `actions.base`, `actions.windows_ops`, `actions.registry`.
  - Add dry-run simulation support.
  - Write unit tests for power actions and mock execution.
- **Phase 3: Background Worker Process**
  - Implement `worker.py` with wall-clock countdown, overdue sleep detection, and 2-minute grace period policy.
  - Test detached execution and PID management.
- **Phase 4: Interactive TUI & Visual Styling**
  - Implement `tui.theme` (black background, blue/white primary, purple/orange accents).
  - Implement `tui.views` with Rich panels, tables, and countdown typography.
  - Implement `tui.app` with keyboard navigation loop and modal controllers.
- **Phase 5: End-to-End Integration, Edge Cases & Verification**
  - Wire up `__main__.py` entry point.
  - Verify complete lifecycle: configure $\to$ confirm $\to$ countdown $\to$ detach $\to$ re-attach $\to$ cancel $\to$ grace period $\to$ execution.
  - Ensure all test suites pass with 100% success.
