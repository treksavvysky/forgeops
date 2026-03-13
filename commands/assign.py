"""Assignment commands — assign, my-issues, agent-tasks."""

from typing import Optional

from rich.console import Console
from rich.table import Table

from core.database import (
    create_assignment,
    create_db_and_tables,
    get_work_item,
    list_items_by_executor,
    transition_work_item,
)
from core.state_engine import InvalidTransitionError
from models import ExecutorType, WorkItemState

console = Console()


def assign(task_id: int, executor: str, executor_type_str: str = "human") -> None:
    engine = create_db_and_tables()

    try:
        etype = ExecutorType(executor_type_str)
    except ValueError:
        console.print(f"[red]Invalid executor type: {executor_type_str}. Use 'human' or 'agent'.[/red]")
        return

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    create_assignment(engine, task_id, executor, etype, actor=executor)

    # Auto-transition to assigned if currently queued or rework_required
    if item.state in (WorkItemState.queued, WorkItemState.rework_required):
        try:
            transition_work_item(engine, task_id, WorkItemState.assigned, actor=executor)
        except InvalidTransitionError:
            pass  # Don't fail the assignment if transition isn't valid

    console.print(f"[green]WI-{task_id} assigned to {executor} ({etype.value})[/green]")


def my_issues(executor: str) -> None:
    engine = create_db_and_tables()
    items = list_items_by_executor(engine, executor)
    _print_items(items, f"Work items assigned to {executor}")


def agent_tasks(executor: str) -> None:
    engine = create_db_and_tables()
    items = list_items_by_executor(engine, executor)
    _print_items(items, f"Work items for agent {executor}")


def _print_items(items: list, title: str) -> None:
    if not items:
        console.print(f"No work items found for this executor.")
        return

    table = Table(title=title)
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("Repository", style="magenta")
    table.add_column("State", no_wrap=True)
    table.add_column("Priority", no_wrap=True)
    table.add_column("Title")

    for item in items:
        blocked = " [red]BLOCKED[/red]" if item.is_blocked else ""
        repo_name = item.repository.name if item.repository else "—"
        table.add_row(
            f"WI-{item.task_id}",
            repo_name,
            item.state.value,
            item.priority.value,
            item.title + blocked,
        )

    console.print(table)
    console.print(f"\nTotal: {len(items)} work item(s)")
