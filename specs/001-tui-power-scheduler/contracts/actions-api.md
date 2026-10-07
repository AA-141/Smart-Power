# Contracts: Power Actions & Background Worker API

**Feature**: `001-tui-power-scheduler`  
**Date**: 2026-09-30

---

## 1. `PowerAction` Interface Contract

Every power action implementation must conform to this interface:

```python
from typing import Protocol, Tuple

class PowerActionHandler(Protocol):
    action_id: str
    display_name: str
    description: str
    is_destructive: bool

    def is_supported(self) -> Tuple[bool, str]:
        """Returns (supported: bool, reason_if_not: str)."""
        ...

    def execute(self, force: bool = False, dry_run: bool = False) -> Tuple[bool, str]:
        """
        Executes the power action on Windows.
        Returns (success: bool, message: str).
        """
        ...

    def abort(self, dry_run: bool = False) -> Tuple[bool, str]:
        """
        Aborts any pending operation if applicable.
        Returns (success: bool, message: str).
        """
        ...
```

---

## 2. Worker Subprocess CLI Contract

When the main TUI confirms a schedule, it spawns the worker process in the background with arguments:

```bash
python -m smart_power.worker --schedule-id <UUID> --action <ACTION> --target <ISO_DATETIME> --mode <MODE>
```

- **Output / Communication**: The worker communicates exclusively by updating `%LOCALAPPDATA%\SmartPower\state.json`.
- **Termination**: The worker terminates cleanly when:
  1. The target action executes.
  2. The schedule is cancelled via `state.json` or SIGTERM/taskkill.
  3. The schedule expires due to overdue wake-up.
