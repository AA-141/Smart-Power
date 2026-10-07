# Quickstart Guide: Smart Power

**Feature**: `001-tui-power-scheduler`  
**Date**: 2026-09-30

---

## 1. Running Smart Power

### Interactive TUI Mode
Launch the application directly with Python 3.10+:

```bash
python -m smart_power
```

Or via direct script invocation:
```bash
python src/smart_power/main.py
```

### Dry-Run / Test Mode (Safe Execution)
To test all UI interactions, countdowns, and timers without actually shutting down or sleeping your PC:

```bash
set SMART_POWER_DRY_RUN=1
python -m smart_power
```

---

## 2. Keyboard Navigation Guide

| Screen | Key | Action |
|---|---|---|
| **Any Menu** | `↑` / `↓` (Up/Down) | Move selection highlight |
| **Any Menu** | `Enter` | Confirm selection / proceed to next step |
| **Duration Input** | Numbers `0-9` + `Enter` | Enter minutes |
| **Time Input** | `HH:MM` + `Enter` | Enter 24h or 12h clock time |
| **Review Dialog** | `Enter` / `y` | Arm schedule and enter live countdown |
| **Review Dialog** | `Esc` / `n` | Return to previous step |
| **Active Countdown**| `c` / `Esc` | Open cancellation confirmation modal |
| **Cancel Modal** | `y` / `Enter` | Confirm cancellation (stops worker and resets) |
| **Cancel Modal** | `n` / `Esc` | Dismiss modal and keep countdown running |
| **Active Countdown**| `q` | Close TUI (schedule remains running in background) |

---

## 3. Running Automated Tests

Run the full automated test suite using Python's standard `unittest`:

```bash
python -m unittest discover tests -v
```
