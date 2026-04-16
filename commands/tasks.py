"""Task hierarchy commands — add-task, list-tasks."""

from typing import Optional

from rich.console import Console
from rich.table import Table

from core.database import (
    create_db_and_tables,
    create_work_item,
    get_child_progress,
    get_work_item,
    list_work_items,
)
from models import Priority

console = Console()


def add_task(
    parent_id: int,
    title: str,
    *,
    description: Optional[str] = None,
    priority: str = "medium",
    created_by: Optional[str] = None,
) -> None:
    engine = create_db_and_tables()

    parent = get_work_item(engine, parent_id)
    if not parent:
        console.print(f"[red]Parent work item WI-{parent_id} not found.[/red]")
        return

    try:
        pri = Priority(priority)
    except ValueError:
        pri = Priority.medium

    # Capture repo name while parent is still usable
    repo_name = parent.repository.name if parent.repository else None

    child = create_work_item(
        engine,
        title,
        repo_name=repo_name,
        description=description,
        priority=pri,
        parent_id=parent_id,
        created_by=created_by,
    )
    console.print(f"[green]Sub-task WI-{child.task_id} created under WI-{parent_id}[/green]")


def list_tasks(parent_id: int) -> None:
    engine = create_db_and_tables()

    parent = get_work_item(engine, parent_id)
    if not parent:
        console.print(f"[red]Work item WI-{parent_id} not found.[/red]")
        return

    children = list_work_items(engine, parent_id=parent_id)
    done, total = get_child_progress(engine, parent_id)

    if not children:
        console.print(f"No sub-tasks for WI-{parent_id}.")
        return

    pct = int(done / total * 100) if total else 0
    console.print(f"[bold]WI-{parent_id}:[/bold] {parent.title}  [{done}/{total} complete — {pct}%]")

    table = Table()
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("State", no_wrap=True)
    table.add_column("Priority", no_wrap=True)
    table.add_column("Title")

    for child in children:
        blocked = " [red]BLOCKED[/red]" if child.is_blocked else ""
        table.add_row(
            f"WI-{child.task_id}",
            child.state.value,
            child.priority.value,
            child.title + blocked,
        )

    console.print(table)
