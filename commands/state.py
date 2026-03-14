"""State engine commands — update-status, block, unblock."""

from typing import Optional

from rich.console import Console

from core.database import (
    block_work_item,
    create_db_and_tables,
    transition_work_item,
    unblock_work_item,
)
from core.state_engine import InvalidTransitionError, RepoConcurrencyError
from models import WorkItemState

console = Console()


def update_status(task_id: int, state_str: str, *, actor: Optional[str] = None) -> None:
    engine = create_db_and_tables()

    try:
        new_state = WorkItemState(state_str)
    except ValueError:
        console.print(f"[red]Unknown state: {state_str}[/red]")
        valid = ", ".join(s.value for s in WorkItemState)
        console.print(f"Valid states: {valid}")
        return

    try:
        item = transition_work_item(engine, task_id, new_state, actor=actor)
        console.print(f"[green]WI-{item.task_id} → {item.state.value}[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
    except InvalidTransitionError as e:
        console.print(f"[red]{e}[/red]")
    except RepoConcurrencyError as e:
        console.print(f"[red]{e}[/red]")


def block(task_id: int, reason: str, *, actor: Optional[str] = None) -> None:
    engine = create_db_and_tables()
    try:
        item = block_work_item(engine, task_id, reason, actor=actor)
        console.print(f"[yellow]WI-{item.task_id} blocked:[/yellow] {reason}")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


def unblock(task_id: int, *, actor: Optional[str] = None) -> None:
    engine = create_db_and_tables()
    try:
        item = unblock_work_item(engine, task_id, actor=actor)
        console.print(f"[green]WI-{item.task_id} unblocked[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
