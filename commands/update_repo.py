"""Update Repository Command - Modify repository metadata."""

from typing import Optional

from rich.console import Console

from core.database import create_db_and_tables
from core.repository_manager import RepositoryManager
from models import RepoStatus

console = Console()


def update_repo(
    repo_name: str,
    *,
    org: Optional[str] = None,
    default_branch: Optional[str] = None,
    status: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
    local_path: Optional[str] = None,
    language: Optional[str] = None,
    deploy_target: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    engine = create_db_and_tables()
    repo_manager = RepositoryManager(engine)

    existing = repo_manager.get_repository(repo_name)
    if not existing:
        console.print(f"[red]Repository '{repo_name}' not found.[/red]")
        return

    updates = {}
    if org is not None:
        updates["org"] = org
    if default_branch is not None:
        updates["default_branch"] = default_branch
    if url is not None:
        updates["url"] = url
    if description is not None:
        updates["description"] = description
    if local_path is not None:
        updates["local_path"] = local_path
    if language is not None:
        updates["language"] = language
    if deploy_target is not None:
        updates["deploy_target"] = deploy_target
    if notes is not None:
        updates["notes"] = notes
    if status is not None:
        try:
            updates["status"] = RepoStatus(status)
        except ValueError:
            console.print(f"[red]Invalid status: {status}. Use 'active' or 'archived'.[/red]")
            return

    if not updates:
        console.print("[yellow]No updates specified.[/yellow]")
        return

    repo_manager.update_repository(repo_name, **updates)
    console.print(f"[green]Repository '{repo_name}' updated.[/green]")
