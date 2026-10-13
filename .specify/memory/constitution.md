# Smart Power Constitution

## Core Principles

### I. Windows-First Python Implementation
- Smart Power is implemented purely in Python and engineered specifically for Microsoft Windows as its primary and supported target platform.
- Operating system interactions leverage Windows-native facilities (standard library `subprocess` invoking Windows utilities like `shutdown.exe`, or `ctypes` invoking Win32 / `Powrprof.dll` APIs) with zero unnecessary platform-abstraction overhead.

### II. Strict Separation of Concerns & Modular Extensibility
- Architectural boundaries must be strictly isolated into independent modules:
  - **UI Layer**: Presentation and user interaction only; contains zero business, timing, or power execution logic.
  - **Application Logic**: Orchestrates workflows, coordinates actions, and validates inputs.
  - **Scheduler / Timing Engine**: Manages timers, delays, and countdowns without coupling to power mechanics.
  - **OS Power Engine**: Encapsulates Windows power operations (shutdown, restart, sleep, hibernate, abort, lock, sign-out).
  - **Configuration**: Handles persistent user settings, defaults, and serialization.
  - **Error & Diagnostic Handling**: Centralizes error translation, user feedback, and diagnostic logging.
- New power actions and scheduling modes must be pluggable via consistent interfaces without modifying core orchestration logic or triggering structural rewrites.

### III. Pragmatic Simplicity & Minimal Abstraction (Anti-Over-Engineering)
- Always prefer direct, clean, and maintainable implementations over speculative design patterns.
- Do not introduce interfaces with a single implementation, multi-level inheritance hierarchies, or configurable layers for fixed system behaviors.
- Follow YAGNI (You Aren't Gonna Need It) strictly: code must solve today's proven requirements, not hypothetical future variations.

### IV. Dependency Economy & Standard Library Preference
- Strictly avoid unnecessary third-party dependencies.
- Rely on the Python standard library (`subprocess`, `ctypes`, `threading`, `dataclasses`, `argparse`, `json`, `logging`, `time`) as the default solution for all core capabilities.
- External dependencies are permitted only when standard library solutions are demonstrably inadequate or fragile (e.g., standard GUI toolkit or system tray integration), and any adopted dependency must be mature, stable, and well-maintained.

### V. Operational Safety & Resilient Error Handling
- Safe execution of system power commands is critical:
  - Destructive or abrupt actions must support confirmation, explicit abort/cancellation windows, and clear progress indication.
  - Never run unverified or shell-injected command strings; use argument lists for process invocation.
- The application must be resilient against runtime failures (e.g., OS permission denial, cancelled schedules, process interruption).
- Unhandled exceptions that crash the application are unacceptable. Failures must be intercepted, translated into actionable user-facing messages, and recorded in diagnostic logs with technical details for debugging.

### VI. Resource Efficiency & Non-Blocking Idle Execution
- Resource footprint (CPU and RAM) must remain minimal, especially while idling or waiting for scheduled power events.
- Busy-wait loops and aggressive polling are strictly forbidden. Timers and background waiting must use non-blocking event-driven synchronization (e.g., `threading.Event.wait` with timeouts or OS sleep primitives).

### VII. Testability & Incremental Evolution
- The codebase must be engineered for automated testing and incremental development from day one.
- The OS Power Engine must support safe mock/dry-run execution to permit thorough unit and integration testing without triggering actual Windows power state transitions.
- All new features must conform to established project patterns and include runnable verification tests.
- Backward compatibility for configuration and core command behavior must be preserved across updates.

### VIII. English User Interface & Consistent Diagnostics
- All user-facing text—including GUI labels, command-line output, dialogues, notification toasts, and user alerts—must be authored consistently in clear English.
- Diagnostic logs and exception details must follow structured, predictable English formatting.

## Architecture & Windows Standards

### Safe Power Operation Contract
- Power actions must define explicit capabilities: `is_supported()`, `requires_elevation()`, `execute()`, and `abort()`.
- Abort mechanisms (e.g., `shutdown /a`) must be readily accessible whenever a timed shutdown/restart is active.
- Admin privilege requirements must be detected gracefully, informing the user with clear instructions rather than failing silently.

### Configuration & State
- User configuration must be persisted in a predictable, user-isolated Windows directory (e.g., `%APPDATA%\SmartPower` or local application directory when portable).
- Corrupted or missing configuration files must fall back to safe defaults without crashing.

## Development & Quality Standards

- **Code Quality**: Adhere to PEP 8, utilize type annotations, and maintain clean module docstrings.
- **Verification Gate**: Any new power action, scheduler enhancement, or logic branch must be accompanied by runnable self-checks or unit tests using simulated OS execution.
- **Diff Discipline**: Keep changes minimal, focused, and aligned with existing conventions. No scaffolding or boilerplate for unrequested features.

## Governance

- This Constitution serves as the single source of truth for architectural, design, and implementation decisions in Smart Power.
- Any proposed deviation (e.g., adding an external library or altering component separation) must be explicitly justified against these core principles.
- Code reviews and automated planning phases must verify adherence to this Constitution.

**Version**: 1.0.0 | **Ratified**: 2026-09-30 | **Last Amended**: 2026-09-30
