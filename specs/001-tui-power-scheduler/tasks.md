# Tasks: Interactive TUI Power Action Scheduler

**Input**: Design documents from `/specs/001-tui-power-scheduler/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/actions-api.md`  
**Organization**: Tasks are grouped by user story and implementation phase to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Target user story (US1, US2, US3, US4, US5)
- Exact file paths are included in task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic package structure

- [x] T001 Initialize project directory layout (`src/smart_power/core`, `src/smart_power/actions`, `src/smart_power/tui`, `tests`)
- [x] T002 [P] Create package markers `src/smart_power/__init__.py`, `src/smart_power/core/__init__.py`, `src/smart_power/actions/__init__.py`, `src/smart_power/tui/__init__.py`
- [x] T003 [P] Configure top-level execution entry points in `src/smart_power/__main__.py` and `src/smart_power/main.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, persistence, and Windows execution engine that all stories depend on

- [x] T004 [P] Implement core enums and `ActiveSchedule` dataclass in `src/smart_power/core/models.py` per `data-model.md`
- [x] T005 [P] Implement time conversion, past-time rollover, and formatting utilities in `src/smart_power/core/timing.py`
- [x] T006 Implement atomic JSON state management and PID verification in `src/smart_power/core/storage.py`
- [x] T007 [P] Implement power action interface protocol and execution result types in `src/smart_power/actions/base.py` per `contracts/actions-api.md`
- [x] T008 Implement Windows native power commands (Shutdown, Restart, Sleep, Lock, Abort) with dry-run support in `src/smart_power/actions/windows_ops.py`
- [x] T009 Implement extensible action registry in `src/smart_power/actions/registry.py` registering the 4 core Windows operations
- [x] T010 [P] Implement visual styling tokens and color constants (black, blue, white, purple, orange) in `src/smart_power/tui/theme.py`

**Checkpoint**: Foundational layer complete. User story implementation can proceed.

---

## Phase 3: User Story 1 - Configure and Confirm Scheduled Action (Priority: P1)

**Goal**: Deliver interactive setup wizard, confirmation screen, and live ticking countdown screen

### Tests for User Story 1
- [x] T011 [P] [US1] Unit tests for exact-time and relative-duration calculations in `tests/test_timing.py`
- [x] T012 [P] [US1] Unit tests for mock Windows action generation and execution in `tests/test_actions.py`

### Implementation for User Story 1
- [x] T013 [US1] Implement TUI wizard screens (mode selector, duration input, clock input, action picker) in `src/smart_power/tui/views.py`
- [x] T014 [US1] Implement review & confirmation dialog view and active countdown dashboard in `src/smart_power/tui/views.py`
- [x] T015 [US1] Implement keyboard navigation loop (Arrow keys, Enter, Esc, Numbers) and screen state transitions in `src/smart_power/tui/app.py`
- [x] T016 [US1] Connect TUI confirmation to schedule activation and live countdown rendering in `src/smart_power/tui/app.py`

**Checkpoint**: User Story 1 functional — user can launch app, configure time, choose action, confirm, and see live countdown.

---

## Phase 4: User Story 2 - Safe Cancellation with Guardrails (Priority: P1)

**Goal**: Provide two-step cancellation modal to prevent accidental schedule termination

### Tests for User Story 2
- [x] T017 [P] [US2] Unit tests for schedule cancellation and Windows abort command generation (`shutdown /a`) in `tests/test_actions.py`

### Implementation for User Story 2
- [x] T018 [US2] Implement cancellation confirmation modal rendering in `src/smart_power/tui/views.py`
- [x] T019 [US2] Wire cancel hotkey (`c` / `Esc`), modal confirm/dismiss logic, and OS abort call in `src/smart_power/tui/app.py`
- [x] T020 [US2] Reset state and return cleanly to setup menu after confirmed cancellation in `src/smart_power/tui/app.py`

**Checkpoint**: User Stories 1 and 2 functional — active countdown can be safely disarmed with confirmation.

---

## Phase 5: User Story 3 - Persistent Background Execution & Single-Schedule Re-attach (Priority: P2)

**Goal**: Allow closing visible TUI while schedule continues running; re-opening TUI re-attaches to live countdown

### Tests for User Story 3
- [x] T021 [P] [US3] Unit tests for atomic state persistence, corrupted file recovery, and process liveness checks in `tests/test_storage.py`

### Implementation for User Story 3
- [x] T022 [US3] Implement headless background runner with non-blocking sleep loop in `src/smart_power/worker.py`
- [x] T023 [US3] Add detached worker spawning (`DETACHED_PROCESS` | `CREATE_NO_WINDOW`) upon schedule confirmation in `src/smart_power/tui/app.py`
- [x] T024 [US3] Implement single-active-schedule detection on startup, bypassing wizard to re-attach to live countdown in `src/smart_power/tui/app.py`
- [x] T025 [US3] Add stale schedule cleanup on reboot (detect dead PID) in `src/smart_power/core/storage.py`

**Checkpoint**: User Stories 1, 2, and 3 functional — closing terminal does not kill schedule; re-launching seamlessly re-attaches.

---

## Phase 6: User Story 4 - Unsaved Work Protection & Conditional 2-Minute Extension (Priority: P2)

**Goal**: Execute without force at target time, and only if blocked by unsaved applications, alert user and grant 2-minute grace period before executing with Force (`/f`)

### Tests for User Story 4
- [x] T026 [P] [US4] Unit tests for conditional 2-minute extension (normal pass vs. blocked escalation to force) in `tests/test_worker_flow.py`

### Implementation for User Story 4
- [x] T027 [US4] Implement initial non-force attempt and block detection in `src/smart_power/worker.py` triggering +120s grace period only when blocked
- [x] T028 [US4] Implement orange high-urgency grace period banner and extended countdown display in `src/smart_power/tui/views.py`
- [x] T029 [US4] Implement final forced execution (`force=True` -> `shutdown /s /f /t 0`) after grace expiration in `src/smart_power/worker.py`

**Checkpoint**: User Story 4 functional — normal actions finish immediately; blocked actions grant 2-minute grace and deterministically force execution upon expiration.

---

## Phase 7: User Story 5 - Overdue Sleep-Wake & Error Handling (Priority: P3)

**Goal**: Prevent late execution after overdue sleep wake-up and provide user-friendly English error views

### Tests for User Story 5
- [x] T030 [P] [US5] Unit tests for overdue clock detection (`now > target_time + threshold`) in `tests/test_timing.py`

### Implementation for User Story 5
- [x] T031 [US5] Implement overdue wake-up check in `src/smart_power/worker.py` (transitions to `EXPIRED_SLEEP`, aborts power action)
- [x] T032 [US5] Implement English error dialogue view for permission denials and overdue cancellations in `src/smart_power/tui/views.py`
- [x] T033 [US5] Add global exception boundaries in `src/smart_power/main.py` preventing unhandled crash tracebacks

**Checkpoint**: All user stories functional and resilient against clock jumps and system errors.

---

## Phase 8: Polish & Verification

**Purpose**: End-to-end verification, dry-run validation, and user documentation

- [x] T034 [P] Verify full test suite execution with `python -m unittest discover tests -v`
- [x] T035 Execute end-to-end dry-run workflow (`SMART_POWER_DRY_RUN=1`) verifying UI transitions and color harmony
- [x] T036 Final code review ensuring zero unhandled exceptions, PEP 8 compliance, and adherence to Project Constitution
