"""Add Repository Command - Add a new repository to the registry."""

from typing import Optional

from rich.console import Console

from core.database import create_db_and_tables, get_repositories
from core.repository_manager import RepositoryManager

console = Console()


def add_repo(
    repo_name: str,
    *,
    org: Optional[str] = None,
    default_branch: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    engine = create_db_and_tables()
    repo_manager = RepositoryManager(engine)

    is_valid, error_msg = repo_manager.validate_repo_name(repo_name)
    if not is_valid:
        console.print(f"[red]Invalid repository name: {error_msg}[/red]")
        return

    success = repo_manager.add_repository(
        repo_name,
        org=org,
        default_branch=default_branch,
        url=url,
        description=description,
    )

    if success:
        repos = get_repositories(engine)
        console.print(f"[green]Repository '{repo_name}' added successfully![/green]")
        console.print(f"Registry now contains {len(repos)} repositories.")
    else:
        console.print(f"[yellow]Repository '{repo_name}' already exists.[/yellow]")
