"""Session continuity commands — status, next, snapshot, resume."""

import json
from datetime import UTC, datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import BASE_DIR
from core.database import (
    create_db_and_tables,
    get_activity_log,
    list_work_items,
)
from models import WorkItemState

console = Console()

SNAPSHOT_FILE = BASE_DIR / ".forgeops_snapshot.json"


def status_overview() -> None:
    engine = create_db_and_tables()
    all_items = list_work_items(engine)

    if not all_items:
        console.print("No work items in the ledger.")
        return

    # Group by state
    by_state: dict[str, list] = {}
    for item in all_items:
        by_state.setdefault(item.state.value, []).append(item)

    # Summary panel
    summary_parts = []
    for state in WorkItemState:
        count = len(by_state.get(state.value, []))
        if count:
            summary_parts.append(f"{state.value}: {count}")
    console.print(Panel(" | ".join(summary_parts), title="[bold]Status Overview[/bold]"))

    # Executing items (with repo concurrency info)
    executing = by_state.get("executing", [])
    if executing:
        table = Table(title="Currently Executing")
        table.add_column("ID", style="bold cyan", no_wrap=True)
        table.add_column("Repository", style="magenta")
        table.add_column("Title")
        for item in executing:
            repo = item.repository.name if item.repository else "—"
            table.add_row(f"WI-{item.task_id}", repo, item.title)
        console.print(table)

    # Blocked items
    blocked = [i for i in all_items if i.is_blocked]
    if blocked:
        table = Table(title="Blocked Items")
        table.add_column("ID", style="bold cyan", no_wrap=True)
        table.add_column("State")
        table.add_column("Reason", style="red")
        table.add_column("Title")
        for item in blocked:
            table.add_row(
                f"WI-{item.task_id}",
                item.state.value,
                item.blocked_reason or "—",
                item.title,
            )
        console.print(table)

    # Awaiting review
    awaiting = by_state.get("awaiting_review", [])
    if awaiting:
        table = Table(title="Awaiting Review")
        table.add_column("ID", style="bold cyan", no_wrap=True)
        table.add_column("Repository", style="magenta")
        table.add_column("Title")
        for item in awaiting:
            repo = item.repository.name if item.repository else "—"
            table.add_row(f"WI-{item.task_id}", repo, item.title)
        console.print(table)

    # Recent activity
    log = get_activity_log(engine, limit=10)
    if log:
        table = Table(title="Recent Activity (last 10)")
        table.add_column("Time", no_wrap=True)
        table.add_column("Item", style="cyan", no_wrap=True)
        table.add_column("Action")
        table.add_column("Detail")
        for entry in log:
            table.add_row(
                str(entry.created_at)[:19],
                f"WI-{entry.task_id}" if entry.task_id else "—",
                entry.action.value,
                entry.detail or "—",
            )
        console.print(table)


def next_actions() -> None:
    engine = create_db_and_tables()

    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}

    items = []
    # Items awaiting review
    items.extend(list_work_items(engine, state=WorkItemState.awaiting_review))
    # Blocked items
    items.extend(list_work_items(engine, is_blocked=True))
    # Rework required
    items.extend(list_work_items(engine, state=WorkItemState.rework_required))

    # Deduplicate
    seen = set()
    unique = []
    for item in items:
        if item.task_id not in seen:
            seen.add(item.task_id)
            unique.append(item)

    # Sort by priority
    unique.sort(key=lambda i: priority_order.get(i.priority.value, 99))

    if not unique:
        console.print("[green]Nothing needs human attention right now.[/green]")
        return

    table = Table(title="Next Actions — Items Needing Attention")
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("State")
    table.add_column("Priority", no_wrap=True)
    table.add_column("Reason")
    table.add_column("Title")

    for item in unique:
        reasons = []
        if item.state == WorkItemState.awaiting_review:
            reasons.append("needs review")
        if item.is_blocked:
            reasons.append(f"blocked: {item.blocked_reason or '?'}")
        if item.state == WorkItemState.rework_required:
            reasons.append("rework required")
        table.add_row(
            f"WI-{item.task_id}",
            item.state.value,
            item.priority.value,
            "; ".join(reasons),
            item.title,
        )

    console.print(table)
    console.print(f"\n{len(unique)} item(s) need attention")


def snapshot() -> None:
    engine = create_db_and_tables()
    all_items = list_work_items(engine)

    data = {
        "snapshot_at": datetime.now(UTC).isoformat(),
        "items": [
            {
                "task_id": item.task_id,
                "title": item.title,
                "state": item.state.value,
                "priority": item.priority.value,
                "is_blocked": item.is_blocked,
                "blocked_reason": item.blocked_reason,
                "repository": item.repository.name if item.repository else None,
            }
            for item in all_items
        ],
    }

    SNAPSHOT_FILE.write_text(json.dumps(data, indent=2))
    console.print(f"[green]Snapshot saved ({len(all_items)} items) → {SNAPSHOT_FILE}[/green]")


def resume() -> None:
    if not SNAPSHOT_FILE.exists():
        console.print("[yellow]No snapshot found. Run 'snapshot' first.[/yellow]")
        return

    data = json.loads(SNAPSHOT_FILE.read_text())
    snap_time = data.get("snapshot_at", "unknown")
    items = data.get("items", [])

    console.print(Panel(f"Snapshot from {snap_time}", title="[bold]Last Session[/bold]"))

    if not items:
        console.print("Snapshot was empty.")
        return

    table = Table()
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("State")
    table.add_column("Priority")
    table.add_column("Repository")
    table.add_column("Title")

    for item in items:
        blocked = " [red]BLOCKED[/red]" if item.get("is_blocked") else ""
        table.add_row(
            f"WI-{item['task_id']}",
            item["state"],
            item["priority"],
            item.get("repository") or "—",
            item["title"] + blocked,
        )

    console.print(table)
    console.print(f"\n{len(items)} item(s) at time of snapshot")
