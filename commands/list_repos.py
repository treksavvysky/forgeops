"""List Repositories Command - Display all repositories with Rich formatting."""

from rich.console import Console
from rich.table import Table

from core.database import create_db_and_tables, get_repositories

console = Console()


def list_repos(include_archived: bool = False) -> None:
    engine = create_db_and_tables()
    repos = get_repositories(engine, include_archived=include_archived)

    if not repos:
        console.print("No repositories found.")
        console.print("Use [bold]add-repo <name>[/bold] to add one.")
        return

    title = "Repositories"
    if include_archived:
        title += " (including archived)"

    table = Table(title=title, show_lines=False)
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Org")
    table.add_column("Branch")
    table.add_column("Status", no_wrap=True)
    table.add_column("URL")
    table.add_column("Description")
    table.add_column("Path")
    table.add_column("Lang")
    table.add_column("Deploy")

    for i, repo in enumerate(repos, 1):
        status_style = "green" if repo.status.value == "active" else "dim"
        table.add_row(
            str(i),
            repo.name,
            repo.org or "—",
            repo.default_branch or "—",
            f"[{status_style}]{repo.status.value}[/{status_style}]",
            repo.url or "—",
            repo.description or "—",
            repo.local_path or "—",
            repo.language or "—",
            repo.deploy_target or "—",
        )

    console.print(table)
    console.print(f"\nTotal: {len(repos)} repository(ies)")
