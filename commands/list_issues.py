"""List Issues Command - Display work items with Rich formatting."""

from typing import Optional

from rich.console import Console
from rich.table import Table

from core.database import create_db_and_tables, list_work_items
from models import Priority, WorkItemState

console = Console()


def list_issues(
    repo_filter: Optional[str] = None,
    state_filter: Optional[str] = None,
    show_blocked: Optional[bool] = None,
    priority_filter: Optional[str] = None,
) -> None:
    engine = create_db_and_tables()

    state = None
    if state_filter:
        try:
            state = WorkItemState(state_filter)
        except ValueError:
            console.print(f"[red]Unknown state: {state_filter}[/red]")
            return

    priority = None
    if priority_filter:
        try:
            priority = Priority(priority_filter)
        except ValueError:
            console.print(f"[red]Unknown priority: {priority_filter}[/red]")
            return

    items = list_work_items(
        engine,
        repo_name=repo_filter,
        state=state,
        is_blocked=show_blocked,
        priority=priority,
    )

    if not items:
        label = ""
        if repo_filter:
            label += f" for repository '{repo_filter}'"
        if state_filter:
            label += f" in state '{state_filter}'"
        console.print(f"No work items found{label}.")
        return

    title = "Work Items"
    if repo_filter:
        title += f" — {repo_filter}"

    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("Repository", style="magenta")
    table.add_column("State", no_wrap=True)
    table.add_column("Priority", no_wrap=True)
    table.add_column("Title")

    state_styles = {
        WorkItemState.queued: "dim",
        WorkItemState.assigned: "blue",
        WorkItemState.executing: "bold yellow",
        WorkItemState.completed: "green",
        WorkItemState.awaiting_review: "bold magenta",
        WorkItemState.accepted: "bold green",
        WorkItemState.rework_required: "bold red",
        WorkItemState.closed: "dim",
    }

    priority_styles = {
        "low": "dim",
        "medium": "",
        "high": "bold yellow",
        "urgent": "bold red",
    }

    for item in items:
        item_id = f"WI-{item.task_id}"
        repo_name = item.repository.name if item.repository else "—"
        state_style = state_styles.get(item.state, "")
        pri_style = priority_styles.get(item.priority.value, "")
        blocked = " [red]BLOCKED[/red]" if item.is_blocked else ""
        title_text = item.title
        if len(title_text) > 60:
            title_text = title_text[:57] + "..."

        state_text = f"[{state_style}]{item.state.value}[/{state_style}]" if state_style else item.state.value
        pri_text = f"[{pri_style}]{item.priority.value}[/{pri_style}]" if pri_style else item.priority.value

        table.add_row(
            item_id,
            repo_name,
            state_text,
            pri_text,
            title_text + blocked,
        )

    console.print(table)
    console.print(f"\nTotal: {len(items)} work item(s)")
