"""Review commands — review-queue, approve, request-changes."""

from typing import Optional

from rich.console import Console
from rich.table import Table

from core.database import (
    create_db_and_tables,
    create_review,
    get_execution_records,
    get_work_item,
    list_work_items,
    transition_work_item,
)
from core.state_engine import InvalidTransitionError
from models import ReviewDecision, WorkItemState

console = Console()


def review_queue() -> None:
    engine = create_db_and_tables()
    items = list_work_items(engine, state=WorkItemState.awaiting_review)
    if not items:
        console.print("No items awaiting review.")
        return

    table = Table(title="Review Queue")
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("Repository", style="magenta")
    table.add_column("Priority", no_wrap=True)
    table.add_column("Title")
    table.add_column("Last Run")

    for item in items:
        repo_name = item.repository.name if item.repository else "—"
        records = get_execution_records(engine, item.task_id)
        last_run = ""
        if records:
            r = records[-1]
            parts = []
            if r.branch:
                parts.append(r.branch)
            if r.commit:
                parts.append(r.commit)
            parts.append(r.status.value)
            last_run = " | ".join(parts)

        blocked = " [red]BLOCKED[/red]" if item.is_blocked else ""
        table.add_row(
            f"WI-{item.task_id}",
            repo_name,
            item.priority.value,
            item.title + blocked,
            last_run or "—",
        )

    console.print(table)
    console.print(f"\nTotal: {len(items)} item(s) awaiting review")


def approve(task_id: int, reviewer: str, *, note: Optional[str] = None) -> None:
    engine = create_db_and_tables()

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    if item.state != WorkItemState.awaiting_review:
        console.print(f"[red]WI-{task_id} is in state '{item.state.value}', not 'awaiting_review'.[/red]")
        return

    create_review(engine, task_id, reviewer, ReviewDecision.accepted, note=note, actor=reviewer)

    try:
        transition_work_item(engine, task_id, WorkItemState.accepted, actor=reviewer)
    except InvalidTransitionError:
        pass

    console.print(f"[green]WI-{task_id} approved by {reviewer}[/green]")


def request_changes(task_id: int, reviewer: str, *, note: Optional[str] = None) -> None:
    engine = create_db_and_tables()

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    if item.state != WorkItemState.awaiting_review:
        console.print(f"[red]WI-{task_id} is in state '{item.state.value}', not 'awaiting_review'.[/red]")
        return

    create_review(engine, task_id, reviewer, ReviewDecision.rework_required, note=note, actor=reviewer)

    try:
        transition_work_item(engine, task_id, WorkItemState.rework_required, actor=reviewer)
    except InvalidTransitionError:
        pass

    console.print(f"[yellow]WI-{task_id} sent back for rework by {reviewer}[/yellow]")
    if note:
        console.print(f"  Note: {note}")
