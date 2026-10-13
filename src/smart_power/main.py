"""Command-line entry point with global safety boundaries."""
from __future__ import annotations

import sys
import traceback


def main(argv=None) -> int:
    try:
        from .tui.app import run
        return run()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001 - boundary converts crashes to English output
        print(f"Smart Power encountered an error: {exc}")
        print("No power action was executed. Please retry with valid input.")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
