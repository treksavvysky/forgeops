"""Execution record commands — log-run, runs."""

import subprocess
from typing import Optional

from rich.console import Console
from rich.table import Table

from core.database import create_db_and_tables, create_execution_record, get_execution_records, get_work_item
from models import ExecutionStatus

console = Console()


def _detect_git_info() -> tuple[Optional[str], Optional[str]]:
    """Auto-detect current branch and latest commit from git."""
    branch = None
    commit = None
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return branch, commit


def log_run(
    task_id: int,
    executor: str,
    status_str: str,
    *,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
    logs_ref: Optional[str] = None,
    artifact_ref: Optional[str] = None,
    auto_detect_git: bool = True,
) -> None:
    engine = create_db_and_tables()

    try:
        status = ExecutionStatus(status_str)
    except ValueError:
        console.print(f"[red]Invalid status: {status_str}. Use 'success', 'failed', or 'partial'.[/red]")
        return

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    if auto_detect_git and not branch and not commit:
        branch, commit = _detect_git_info()

    record = create_execution_record(
        engine, task_id, executor, status,
        branch=branch, commit=commit,
        logs_ref=logs_ref, artifact_ref=artifact_ref,
        actor=executor,
    )
    console.print(f"[green]Run {record.run_id} logged for WI-{task_id} ({status.value})[/green]")
    if branch or commit:
        console.print(f"  Branch: {branch or '—'}  Commit: {commit or '—'}")


def runs(task_id: int) -> None:
    engine = create_db_and_tables()

    item = get_work_item(engine, task_id)
    if not item:
        console.print(f"[red]Work item WI-{task_id} not found.[/red]")
        return

    records = get_execution_records(engine, task_id)
    if not records:
        console.print(f"No execution records for WI-{task_id}.")
        return

    table = Table(title=f"Execution Records — WI-{task_id}")
    table.add_column("Run", style="bold cyan", no_wrap=True)
    table.add_column("Executor")
    table.add_column("Status", no_wrap=True)
    table.add_column("Branch")
    table.add_column("Commit")
    table.add_column("Created")

    status_styles = {"success": "green", "failed": "red", "partial": "yellow"}

    for r in records:
        style = status_styles.get(r.status.value, "")
        status_text = f"[{style}]{r.status.value}[/{style}]" if style else r.status.value
        table.add_row(
            str(r.run_id),
            r.executor,
            status_text,
            r.branch or "—",
            r.commit or "—",
            str(r.created_at)[:19],
        )

    console.print(table)
