#!/usr/bin/env python3
"""ForgeOps - Cross-repo work ledger for AI-assisted development.

CLI entry point.
"""

from typing import Optional

import typer

from core.database import create_db_and_tables, get_repositories

from commands.add_repo import add_repo as _add_repo
from commands.create_issue import create_issue as _create_issue
from commands.list_issues import list_issues as _list_issues
from commands.list_repos import list_repos as _list_repos
from commands.migrate_issues import migrate_issues as _migrate_issues
from commands.remove_repo import remove_repo as _remove_repo
from commands.update_repo import update_repo as _update_repo
from commands.view_issue import view_issue as _view_issue

app = typer.Typer(help="ForgeOps - Work Ledger")


def _complete_repo(incomplete: str) -> list[str]:
    """Typer autocompletion callback for --repo values."""
    try:
        engine = create_db_and_tables()
        repos = get_repositories(engine, include_archived=False)
        return [r.name for r in repos if r.name.startswith(incomplete)]
    except Exception:
        return []


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
):
    """List work items, optionally filtered."""
    _list_issues(repo_filter=repo, state_filter=state, show_blocked=blocked)


@app.command()
def view_issue(issue_id: str = typer.Argument(help="Work item ID (e.g. WI-1 or 1)")):
    """View detailed information for a specific work item."""
    _view_issue(issue_id)


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
):
    """Add a new repository to the registry."""
    _add_repo(repo_name, org=org, default_branch=branch, url=url, description=description)


@app.command()
def update_repo(
    repo_name: str = typer.Argument(help="Repository name to update"),
    org: Optional[str] = typer.Option(None, "--org", help="Organization"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Default branch"),
    status: Optional[str] = typer.Option(None, "--status", help="Status: active or archived"),
    url: Optional[str] = typer.Option(None, "--url", help="Repository URL"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
):
    """Update repository metadata."""
    _update_repo(repo_name, org=org, default_branch=branch, status=status, url=url, description=description)


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
