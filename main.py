#!/usr/bin/env python3
"""ForgeOps - Cross-repo work ledger for AI-assisted development.

CLI entry point.
"""

from typing import Optional

import typer

from core.database import create_db_and_tables, get_repositories

from commands.add_repo import add_repo as _add_repo
from commands.assign import agent_tasks as _agent_tasks
from commands.assign import assign as _assign
from commands.assign import my_issues as _my_issues
from commands.attachments import attach as _attach
from commands.attachments import list_attachments as _list_attachments
from commands.create_issue import create_issue as _create_issue
from commands.execution import log_run as _log_run
from commands.execution import runs as _runs
from commands.list_issues import list_issues as _list_issues
from commands.list_repos import list_repos as _list_repos
from commands.migrate_issues import migrate_issues as _migrate_issues
from commands.remove_repo import remove_repo as _remove_repo
from commands.review import approve as _approve
from commands.review import request_changes as _request_changes
from commands.review import review_queue as _review_queue
from commands.session import next_actions as _next_actions
from commands.session import resume as _resume
from commands.session import snapshot as _snapshot
from commands.session import status_overview as _status_overview
from commands.state import block as _block
from commands.state import unblock as _unblock
from commands.state import update_status as _update_status
from commands.tasks import add_task as _add_task
from commands.tasks import list_tasks as _list_tasks
from commands.update_repo import update_repo as _update_repo
from commands.delete_issue import delete_issue as _delete_issue
from commands.view_issue import view_issue as _view_issue

app = typer.Typer(help="ForgeOps - Work Ledger")


def _complete_repo(incomplete: str) -> list[str]:
    try:
        engine = create_db_and_tables()
        repos = get_repositories(engine, include_archived=False)
        return [r.name for r in repos if r.name.startswith(incomplete)]
    except Exception:
        return []


def _parse_id(raw: str) -> int:
    """Parse WI-N or plain N into integer. Raises typer.BadParameter on failure."""
    raw = raw.strip()
    if raw.upper().startswith("WI-"):
        raw = raw[3:]
    if raw.upper().startswith("ISSUE-"):
        raw = raw[6:]
    try:
        return int(raw)
    except ValueError:
        raise typer.BadParameter(f"Invalid work item ID: {raw}")


# --- Work Items ---------------------------------------------------------------


@app.command()
def create_issue(
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority: low, medium, high, urgent"),
    created_by: Optional[str] = typer.Option(None, "--created-by", help="Creator identifier"),
):
    """Create a new work item interactively."""
    _create_issue(priority=priority, created_by=created_by)


@app.command()
def list_issues(
    repo: Optional[str] = typer.Option(None, "--repo", help="Filter by repository name", autocompletion=_complete_repo),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state (e.g. queued, executing)"),
    blocked: Optional[bool] = typer.Option(None, "--blocked", help="Filter blocked items"),
    priority: Optional[str] = typer.Option(None, "--priority", help="Filter by priority (low, medium, high, urgent)"),
):
    """List work items, optionally filtered."""
    _list_issues(repo_filter=repo, state_filter=state, show_blocked=blocked, priority_filter=priority)


@app.command()
def view_issue(issue_id: str = typer.Argument(help="Work item ID (e.g. WI-1 or 1)")):
    """View detailed information for a specific work item."""
    _view_issue(issue_id)


@app.command()
def delete_issue(task_id: int = typer.Argument(help="Work item ID to delete")):
    """Delete a work item permanently."""
    _delete_issue(task_id)


# --- State Engine -------------------------------------------------------------


@app.command()
def update_status(
    issue_id: str = typer.Argument(help="Work item ID"),
    state: str = typer.Option(..., "--state", "-s", help="Target state"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Who is making the change"),
):
    """Transition a work item to a new state (with validation)."""
    _update_status(_parse_id(issue_id), state, actor=actor)


@app.command()
def block(
    issue_id: str = typer.Argument(help="Work item ID"),
    reason: str = typer.Option(..., "--reason", "-r", help="Reason for blocking"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Who is blocking"),
):
    """Block a work item with a reason."""
    _block(_parse_id(issue_id), reason, actor=actor)


@app.command()
def unblock(
    issue_id: str = typer.Argument(help="Work item ID"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Who is unblocking"),
):
    """Unblock a work item."""
    _unblock(_parse_id(issue_id), actor=actor)


# --- Assignments --------------------------------------------------------------


@app.command()
def assign(
    issue_id: str = typer.Argument(help="Work item ID"),
    executor: str = typer.Argument(help="Executor name"),
    type: str = typer.Option("human", "--type", "-t", help="Executor type: human or agent"),
):
    """Assign a work item to an executor."""
    _assign(_parse_id(issue_id), executor, type)


@app.command()
def my_issues(
    executor: str = typer.Argument(help="Your executor name"),
):
    """List work items assigned to you."""
    _my_issues(executor)


@app.command()
def agent_tasks(
    executor: str = typer.Argument(help="Agent executor name"),
):
    """List work items assigned to an agent."""
    _agent_tasks(executor)


# --- Execution Records --------------------------------------------------------


@app.command()
def log_run(
    issue_id: str = typer.Argument(help="Work item ID"),
    executor: str = typer.Option(..., "--executor", "-e", help="Who executed"),
    status: str = typer.Option(..., "--status", "-s", help="Outcome: success, failed, partial"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Git branch (auto-detected if omitted)"),
    commit: Optional[str] = typer.Option(None, "--commit", help="Git commit (auto-detected if omitted)"),
    logs_ref: Optional[str] = typer.Option(None, "--logs", help="Reference to logs"),
    artifact_ref: Optional[str] = typer.Option(None, "--artifact", help="Reference to artifact"),
):
    """Log an execution record for a work item."""
    _log_run(
        _parse_id(issue_id),
        executor,
        status,
        branch=branch,
        commit=commit,
        logs_ref=logs_ref,
        artifact_ref=artifact_ref,
    )


@app.command()
def runs(
    issue_id: str = typer.Argument(help="Work item ID"),
):
    """List execution records for a work item."""
    _runs(_parse_id(issue_id))


# --- Reviews ------------------------------------------------------------------


@app.command()
def review_queue():
    """Show work items awaiting review with execution context."""
    _review_queue()


@app.command()
def approve(
    issue_id: str = typer.Argument(help="Work item ID"),
    reviewer: str = typer.Option(..., "--reviewer", "-r", help="Reviewer name"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Review note"),
):
    """Approve a work item (moves from awaiting_review to accepted)."""
    _approve(_parse_id(issue_id), reviewer, note=note)


@app.command()
def request_changes(
    issue_id: str = typer.Argument(help="Work item ID"),
    reviewer: str = typer.Option(..., "--reviewer", "-r", help="Reviewer name"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="What needs to change"),
):
    """Request changes on a work item (moves to rework_required)."""
    _request_changes(_parse_id(issue_id), reviewer, note=note)


# --- Session Continuity -------------------------------------------------------


@app.command()
def status():
    """Overview of where things stand across all work items."""
    _status_overview()


@app.command(name="next")
def next_actions():
    """Show highest-priority items needing human attention."""
    _next_actions()


@app.command()
def snapshot():
    """Capture current state of all work items for later resume."""
    _snapshot()


@app.command()
def resume():
    """Show the snapshot from the last session."""
    _resume()


# --- Attachments --------------------------------------------------------------


@app.command()
def attach(
    issue_id: str = typer.Argument(help="Work item ID"),
    url_or_path: str = typer.Argument(help="URL or file path to attach"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Label for the attachment"),
):
    """Attach a URL or file path to a work item."""
    _attach(_parse_id(issue_id), url_or_path, label=label)


@app.command()
def list_attachments(
    issue_id: str = typer.Argument(help="Work item ID"),
):
    """List attachments for a work item."""
    _list_attachments(_parse_id(issue_id))


# --- Task Hierarchy -----------------------------------------------------------


@app.command()
def add_task(
    parent_id: str = typer.Argument(help="Parent work item ID"),
    title: str = typer.Argument(help="Sub-task title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority"),
    created_by: Optional[str] = typer.Option(None, "--created-by", help="Creator"),
):
    """Create a sub-task under an existing work item."""
    _add_task(_parse_id(parent_id), title, description=description, priority=priority, created_by=created_by)


@app.command()
def list_tasks(
    parent_id: str = typer.Argument(help="Parent work item ID"),
):
    """List sub-tasks of a work item with progress rollup."""
    _list_tasks(_parse_id(parent_id))


# --- Repositories -------------------------------------------------------------


@app.command()
def list_repos(
    all: bool = typer.Option(False, "--all", "-a", help="Include archived repositories"),
):
    """List registered repositories."""
    _list_repos(include_archived=all)


@app.command()
def add_repo(
    repo_name: str = typer.Argument(help="Repository name"),
    org: Optional[str] = typer.Option(None, "--org", help="Organization"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Default branch"),
    url: Optional[str] = typer.Option(None, "--url", help="Repository URL"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    local_path: Optional[str] = typer.Option(None, "--path", help="Local filesystem path"),
    language: Optional[str] = typer.Option(None, "--lang", help="Primary language/stack"),
    deploy_target: Optional[str] = typer.Option(None, "--deploy", help="Deploy target (docker, vercel, etc.)"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Dev environment notes"),
):
    """Add a new repository to the registry."""
    _add_repo(
        repo_name,
        org=org,
        default_branch=branch,
        url=url,
        description=description,
        local_path=local_path,
        language=language,
        deploy_target=deploy_target,
        notes=notes,
    )


@app.command()
def update_repo(
    repo_name: str = typer.Argument(help="Repository name to update"),
    org: Optional[str] = typer.Option(None, "--org", help="Organization"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Default branch"),
    status: Optional[str] = typer.Option(None, "--status", help="Status: active or archived"),
    url: Optional[str] = typer.Option(None, "--url", help="Repository URL"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    local_path: Optional[str] = typer.Option(None, "--path", help="Local filesystem path"),
    language: Optional[str] = typer.Option(None, "--lang", help="Primary language/stack"),
    deploy_target: Optional[str] = typer.Option(None, "--deploy", help="Deploy target (docker, vercel, etc.)"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Dev environment notes"),
):
    """Update repository metadata."""
    _update_repo(
        repo_name,
        org=org,
        default_branch=branch,
        status=status,
        url=url,
        description=description,
        local_path=local_path,
        language=language,
        deploy_target=deploy_target,
        notes=notes,
    )


@app.command()
def remove_repo(repo_name: str = typer.Argument(help="Repository name to remove")):
    """Remove a repository from the registry."""
    _remove_repo(repo_name)


# --- Migration ----------------------------------------------------------------


@app.command()
def migrate_issues():
    """Migrate legacy JSON data into the unified database."""
    _migrate_issues()


if __name__ == "__main__":
    app()
