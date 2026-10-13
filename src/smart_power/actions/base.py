"""Power-action protocol shared by executors and the registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Tuple


@dataclass
class ActionResult:
    success: bool
    message: str
    blocked: bool = False


class PowerActionHandler(Protocol):
    action_id: str
    display_name: str
    description: str
    is_destructive: bool

    def is_supported(self) -> Tuple[bool, str]:
        ...

    def execute(self, force: bool = False, dry_run: bool = False) -> ActionResult:
        ...

    def abort(self, dry_run: bool = False) -> ActionResult:
        ...
