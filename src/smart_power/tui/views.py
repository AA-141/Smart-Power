"""Pure rendering helpers: menus, dialogs, countdown, and error views."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..actions.base import PowerActionHandler
from ..core import timing
from ..core.models import ActiveSchedule
from . import theme


def _menu_table(title: str, options: Sequence[str], selected: int, hint: str) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1))
    for index, option in enumerate(options):
        marker = "[>] " if index == selected else "    "
        style = f"bold {theme.PRIMARY_TEXT}" if index == selected else theme.DIM_TEXT
        table.add_row(f"{marker}{option}", style=style)
    footer = Text(hint, style=theme.DIM_TEXT)
    body = Table.grid(padding=(0, 0))
    body.add_row(table)
    body.add_row(footer)
    return Panel(body, title=f"[bold {theme.TITLE_PURPLE}]{title}[/]",
                 border_style=theme.BORDER_BLUE, padding=(1, 2))


def main_menu(selected: int = 0) -> Panel:
    return _menu_table(
        "SMART POWER",
        ["Schedule with relative duration", "Schedule with exact clock time", "Exit"],
        selected,
        "Use Up/Down + Enter. Press Q to quit.",
    )


def action_menu(actions: Sequence[PowerActionHandler], selected: int = 0) -> Panel:
    labels = [f"{action.display_name} - {action.description}" for action in actions]
    return _menu_table("CHOOSE POWER ACTION", labels, selected, "Use Up/Down + Enter. Press Esc to go back.")


def text_input(title: str, prompt: str, current: str, error: str = "", example: str = "") -> Panel:
    body = Table.grid(padding=(0, 0))
    body.add_row(Text(prompt, style=theme.PRIMARY_TEXT))
    body.add_row(Text(f"> {current}_", style=f"bold {theme.ACCENT_BLUE}"))
    if example:
        body.add_row(Text(f"Example: {example}", style=theme.DIM_TEXT))
    if error:
        body.add_row(Text(error, style=f"bold {theme.WARNING_ORANGE}"))
    body.add_row(Text("Enter confirms. Esc goes back.", style=theme.DIM_TEXT))
    return Panel(body, title=f"[bold {theme.TITLE_PURPLE}]{title}[/]",
                 border_style=theme.BORDER_BLUE, padding=(1, 2))


def review_panel(action: PowerActionHandler, target: datetime, seconds: float) -> Panel:
    body = Table.grid(padding=(0, 1))
    body.add_row(Text("Action:", style=theme.DIM_TEXT), Text(action.display_name, style=f"bold {theme.PRIMARY_TEXT}"))
    body.add_row(Text("Runs at:", style=theme.DIM_TEXT), Text(timing.format_target(target), style=theme.PRIMARY_TEXT))
    body.add_row(Text("In:", style=theme.DIM_TEXT), Text(timing.format_duration(seconds), style=theme.PRIMARY_TEXT))
    body.add_row(Text("Safety:", style=theme.DIM_TEXT),
                 Text("Standard attempt first; 2-minute grace only if blocked.", style=theme.DIM_TEXT))
    body.add_row(Text("Press Enter or Y to confirm. N/Esc goes back.", style=theme.DIM_TEXT))
    return Panel(body, title=f"[bold {theme.WARNING_ORANGE}]REVIEW SCHEDULE[/]",
                 border_style=theme.WARNING_ORANGE, padding=(1, 2))


def countdown_panel(schedule: ActiveSchedule, actions: Sequence[PowerActionHandler],
                    now: Optional[datetime] = None) -> Panel:
    now = now or datetime.now()
    action_id = schedule.action.value if hasattr(schedule.action, "value") else str(schedule.action)
    status_value = schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status)
    label = action_id
    for action in actions:
        if action.action_id == action_id:
            label = action.display_name
            break
    remaining = schedule.remaining_seconds(now)
    big = Text(timing.format_countdown(remaining), style=theme.COUNTDOWN_BIG, justify="center")
    badge = Text("ACTIVE SCHEDULE", style=f"bold {theme.ACCENT_BLUE}")
    if status_value == "grace_period":
        badge = Text("GRACE PERIOD - SAVE YOUR WORK", style=f"bold {theme.WARNING_ORANGE}")
    target = schedule.target_datetime
    body = Table.grid(padding=(0, 0))
    body.add_row(Align.center(badge))
    body.add_row(Align.center(big))
    body.add_row(Align.center(Text(label, style=f"bold {theme.PRIMARY_TEXT}")))
    body.add_row(Align.center(Text(f"Runs at {timing.format_target(target)}", style=theme.DIM_TEXT)))
    if status_value == "grace_period":
        body.add_row(Align.center(Text("Blocked apps detected. Forced run follows this grace period.",
                                       style=f"bold {theme.WARNING_ORANGE}")))
    body.add_row(Align.center(Text("Press C/Esc to cancel. Press Q to hide this window.", style=theme.DIM_TEXT)))
    return Panel(body, title=f"[bold {theme.TITLE_PURPLE}]SMART POWER[/]",
                 border_style=theme.BORDER_BLUE, padding=(1, 2))


def confirm_panel(title: str, question: str) -> Panel:
    body = Table.grid(padding=(0, 0))
    body.add_row(Text(question, style=f"bold {theme.PRIMARY_TEXT}"))
    body.add_row(Text("Press Y/Enter for Yes, N/Esc for No.", style=theme.DIM_TEXT))
    return Panel(body, title=f"[bold {theme.WARNING_ORANGE}]{title}[/]",
                 border_style=theme.WARNING_ORANGE, padding=(1, 2))


def info_panel(title: str, lines: List[str], style: str = "") -> Panel:
    body = Table.grid(padding=(0, 0))
    for line in lines:
        body.add_row(Text(line, style=style or theme.PRIMARY_TEXT))
    body.add_row(Text("Press any key to continue.", style=theme.DIM_TEXT))
    return Panel(body, title=f"[bold {theme.TITLE_PURPLE}]{title}[/]",
                 border_style=theme.BORDER_BLUE, padding=(1, 2))


def error_panel(message: str) -> Panel:
    return info_panel("ERROR", [message], style=f"bold {theme.ERROR_RED}")
