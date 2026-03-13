"""Remove Repository Command - Delete a repository from the registry."""

from rich.console import Console

from core.database import create_db_and_tables
from core.repository_manager import RepositoryManager

console = Console()


def remove_repo(repo_name: str) -> None:
    engine = create_db_and_tables()
    repo_manager = RepositoryManager(engine)

    existing = repo_manager.get_repository(repo_name)
    if not existing:
        console.print(f"[red]Repository '{repo_name}' not found.[/red]")
        return

    success = repo_manager.remove_repository(repo_name)
    if success:
        console.print(f"[green]Repository '{repo_name}' removed.[/green]")
    else:
        console.print(f"[red]Failed to remove '{repo_name}'.[/red]")
