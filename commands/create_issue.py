"""Create Issue Command - Interactive work item creation."""

import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.database import add_repository, create_db_and_tables, create_work_item
from core.repository_manager import RepositoryManager
from models import Priority
from utils.validators import InputValidator

console = Console()


def create_issue(
    priority: str = "medium",
    created_by: Optional[str] = None,
) -> None:
    engine = create_db_and_tables()
    repo_manager = RepositoryManager(engine)
    validator = InputValidator()

    console.print("[bold]Creating a new work item...[/bold]")
    console.print("Press Ctrl+C at any time to cancel.\n")

    title = validator.get_user_input("Title: ", required=True)

    while True:
        repo_name = validator.get_user_input(
            "Repository name: ",
            required=True,
            validator=repo_manager.validate_repo_name,
        )
        confirmed_repo = _confirm_repository(repo_manager, repo_name)
        if confirmed_repo:
            repo_name = confirmed_repo
            break
        console.print("Please enter a repository name.\n")

    description = validator.get_user_input("Description (optional): ", required=False)

    # Ensure repo exists in DB
    add_repository(engine, repo_name)

    try:
        pri = Priority(priority)
    except ValueError:
        pri = Priority.medium

    # Preview
    tbl = Table(show_header=False, box=None, padding=(0, 2))
    tbl.add_column(style="bold cyan")
    tbl.add_column()
    tbl.add_row("Title", title)
    tbl.add_row("Repository", repo_name)
    tbl.add_row("Priority", pri.value)
    tbl.add_row("Description", description or "(none)")
    if created_by:
        tbl.add_row("Created by", created_by)
    console.print(Panel(tbl, title="[bold]Work Item Preview[/bold]"))

    try:
        confirm = input("\nCreate this work item? (Y/n): ").strip().lower()
        if confirm in ("", "y", "yes"):
            item = create_work_item(
                engine,
                title,
                repo_name=repo_name,
                description=description or None,
                priority=pri,
                created_by=created_by,
            )
            console.print(f"\n[green]Work item WI-{item.task_id} created successfully![/green]")
        else:
            console.print("\n[yellow]Cancelled.[/yellow]")
    except KeyboardInterrupt:
        console.print("\n\nOperation cancelled by user.")
        sys.exit(0)


def _confirm_repository(repo_manager: RepositoryManager, repo_name: str) -> Optional[str]:
    repos = repo_manager.load_repositories()
    if repo_name in repos:
        return repo_name

    exact_match, suggestions = repo_manager.suggest_repositories(repo_name)
    if exact_match:
        return repo_name

    if suggestions:
        console.print(f"\nRepository [bold]{repo_name}[/bold] not found in registry.")
        console.print("Did you mean one of these?")
        for i, s in enumerate(suggestions, 1):
            console.print(f"  {i}. {s}")
        console.print(f"  {len(suggestions) + 1}. Use '{repo_name}' anyway")
        console.print(f"  {len(suggestions) + 2}. Enter a different name")
        try:
            choice = input(f"\nSelect option (1-{len(suggestions) + 2}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(suggestions):
                return suggestions[choice_num - 1]
            if choice_num == len(suggestions) + 1:
                return repo_name
            return None
        except (KeyboardInterrupt, ValueError):
            return None
    else:
        try:
            use_anyway = input(f"Repository '{repo_name}' not found. Use it anyway? (y/N): ").strip().lower()
            if use_anyway in ("y", "yes"):
                return repo_name
            return None
        except KeyboardInterrupt:
            console.print("\n\nOperation cancelled by user.")
            sys.exit(0)
