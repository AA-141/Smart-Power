"""Pluggable registry for supported power actions."""
from __future__ import annotations

from typing import Dict, List

from .base import PowerActionHandler
from .windows_ops import LOCK_ACTION, RESTART_ACTION, SHUTDOWN_ACTION, SLEEP_ACTION

_REGISTRY: Dict[str, PowerActionHandler] = {}


def register(action: PowerActionHandler) -> PowerActionHandler:
    _REGISTRY[action.action_id] = action
    return action


def get(action_id: str) -> PowerActionHandler:
    return _REGISTRY[str(action_id)]


def all_actions() -> List[PowerActionHandler]:
    return [get(action_id) for action_id in ("shutdown", "restart", "sleep", "lock")]


for _action in (SHUTDOWN_ACTION, RESTART_ACTION, SLEEP_ACTION, LOCK_ACTION):
    register(_action)
