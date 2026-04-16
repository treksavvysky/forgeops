"""Delete Work Item Command - Remove a work item from the ledger."""

from rich.console import Console

from core.database import create_db_and_tables, delete_work_item, get_work_item

console = Console()


def delete_issue(task_id: int) -> None:
    engine = create_db_and_tables()

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item {task_id} not found.[/red]")
        return

    title = item.title
    deleted = delete_work_item(engine, task_id, actor="cli")
    if deleted:
        console.print(f"[green]Deleted WI-{task_id}: {title}[/green]")
    else:
        console.print(f"[red]Failed to delete WI-{task_id}.[/red]")
