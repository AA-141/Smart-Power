# Smart Power

Windows-first desktop utility with an interactive Terminal User Interface (TUI) for scheduling system power actions.

## Features
- **Interactive TUI**: Clean black/blue/white visual layout with purple titles and orange alerts.
- **Flexible Timing**: Schedule via relative duration (`25m`, `2h`) or exact clock time (`15:30`, `3:30 PM`) with next-day rollover.
- **4 Core Actions**: Shutdown, Restart, Sleep, and Lock.
- **Safety First**: Two-step confirmation gates for scheduling and cancellation.
- **Unsaved Work Protection**: Non-forced execution is attempted first; only if blocked by running applications does Smart Power grant an extra 2-minute grace period before applying forced execution (`/f`).
- **Detached Execution**: Closing the terminal window does not cancel the schedule. Reopening Smart Power re-attaches directly to the live countdown.
- **Overdue Detection**: If the machine wakes from Sleep past the target time, the action safely aborts with an alert instead of executing unexpectedly.

## Running Smart Power

### Standard interactive mode:
```powershell
python -m src.smart_power
```
Or with `PYTHONPATH=src`:
```powershell
python -m smart_power
```

### Safe Dry-Run Mode (No real power actions executed):
```powershell
$env:SMART_POWER_DRY_RUN="1"
python -m src.smart_power
```

## Running the Automated Test Suite:
```powershell
python -m unittest discover tests -v
```
