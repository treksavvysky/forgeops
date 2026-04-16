"""View Issue Command - Display detailed view of a specific work item."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.database import create_db_and_tables, get_work_item, list_work_items

console = Console()


def view_issue(issue_id: str) -> None:
    engine = create_db_and_tables()

    # Accept both "WI-<n>" and plain integer
    task_id = _parse_id(issue_id)
    if task_id is None:
        console.print(f"[red]Invalid work item ID: {issue_id}[/red]")
        console.print("Expected format: WI-<number> (e.g. WI-1) or a plain number.")
        return

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item {issue_id} not found.[/red]")
        _suggest_recent(engine)
        return

    tbl = Table(show_header=False, box=None, padding=(0, 2))
    tbl.add_column(style="bold cyan", min_width=14)
    tbl.add_column()
    tbl.add_row("ID", f"WI-{item.task_id}")
    tbl.add_row("Title", item.title)
    tbl.add_row("Repository", item.repository.name if item.repository else "—")
    tbl.add_row("State", item.state.value)
    tbl.add_row("Priority", item.priority.value)
    tbl.add_row("Blocked", f"Yes — {item.blocked_reason}" if item.is_blocked else "No")
    if item.created_by:
        tbl.add_row("Created by", item.created_by)
    tbl.add_row("Created", str(item.created_at))
    tbl.add_row("Updated", str(item.updated_at))

    if item.description:
        tbl.add_row("Description", item.description)
    else:
        tbl.add_row("Description", "[dim](none)[/dim]")

    console.print(Panel(tbl, title=f"[bold]WI-{item.task_id}[/bold]"))


def _parse_id(raw: str) -> int | None:
    raw = raw.strip()
    if raw.upper().startswith("WI-"):
        raw = raw[3:]
    # Also accept legacy ISSUE-NNN format
    if raw.upper().startswith("ISSUE-"):
        raw = raw[6:]
    try:
        return int(raw)
    except ValueError:
        return None


def _suggest_recent(engine) -> None:
    items = list_work_items(engine)
    if items:
        console.print("\nRecent work items:")
        for item in items[-5:]:
            console.print(f"  WI-{item.task_id}  {item.title}")
