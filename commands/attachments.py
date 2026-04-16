"""Attachment commands — attach, list-attachments."""

from typing import Optional

from rich.console import Console
from rich.table import Table

from core.database import create_attachment, create_db_and_tables, get_attachments, get_work_item

console = Console()


def attach(task_id: int, url_or_path: str, *, label: Optional[str] = None) -> None:
    engine = create_db_and_tables()

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    create_attachment(engine, task_id, url_or_path, label=label)
    console.print(f"[green]Attachment added to WI-{task_id}:[/green] {url_or_path}")


def list_attachments(task_id: int) -> None:
    engine = create_db_and_tables()

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    atts = get_attachments(engine, task_id)
    if not atts:
        console.print(f"No attachments for WI-{task_id}.")
        return

    table = Table(title=f"Attachments — WI-{task_id}")
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("URL / Path")
    table.add_column("Label")
    table.add_column("Added", no_wrap=True)

    for i, att in enumerate(atts, 1):
        table.add_row(
            str(i),
            att.url_or_path,
            att.label or "—",
            str(att.created_at)[:19],
        )

    console.print(table)
