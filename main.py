#!/usr/bin/env python3
"""
ForgeOps - Issue Tracking System
CLI entry point for issue management commands.
"""

from typing import Optional

import typer

from commands.create_issue import create_issue as _create_issue
from commands.list_issues import list_issues as _list_issues
from commands.view_issue import view_issue as _view_issue
from commands.list_repos import list_repos as _list_repos
from commands.add_repo import add_repo as _add_repo
from commands.migrate_issues import migrate_issues as _migrate_issues

app = typer.Typer(help="ForgeOps - Issue Tracker")


@app.command()
def create_issue():
    """Create a new issue interactively."""
    _create_issue()


@app.command()
def list_issues(repo: Optional[str] = typer.Option(None, "--repo", help="Filter by repository name")):
    """List all issues, optionally filtered by repository."""
    _list_issues(repo)


@app.command()
def view_issue(issue_id: str = typer.Argument(help="Issue ID (e.g. ISSUE-001)")):
    """View detailed information for a specific issue."""
    _view_issue(issue_id)


@app.command()
def list_repos():
    """List all registered repositories."""
    _list_repos()


@app.command()
def add_repo(repo_name: str = typer.Argument(help="Repository name to add")):
    """Add a new repository to the registry."""
    _add_repo(repo_name)


@app.command()
def migrate_issues():
    """Import issue JSON files into the SQLite database."""
    _migrate_issues()


if __name__ == "__main__":
    app()
