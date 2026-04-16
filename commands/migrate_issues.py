"""Migrate legacy data (JSON files + old SQLite) into the new unified schema."""

import json
from pathlib import Path

from rich.console import Console

from config import LEGACY_ISSUES_DIR, LEGACY_REPOS_FILE, LEGACY_TASK_LISTS_DIR
from core.database import add_repository, create_db_and_tables, create_work_item
from models import Priority

console = Console()


def migrate_issues() -> None:
    engine = create_db_and_tables()

    repo_count = 0
    item_count = 0

    # --- Migrate repos.json ---------------------------------------------------
    repos_file = Path(LEGACY_REPOS_FILE)
    if repos_file.exists():
        try:
            data = json.loads(repos_file.read_text())
            for name in data.get("repositories", []):
                add_repository(engine, name)
                repo_count += 1
        except (json.JSONDecodeError, IOError) as e:
            console.print(f"[yellow]Warning: could not read {repos_file}: {e}[/yellow]")

    # --- Migrate issues/*.json ------------------------------------------------
    issues_dir = Path(LEGACY_ISSUES_DIR)
    if issues_dir.is_dir():
        for issue_file in sorted(issues_dir.glob("ISSUE-*.json")):
            try:
                issue = json.loads(issue_file.read_text())
                repo_name = issue.get("repository")
                if repo_name:
                    add_repository(engine, repo_name)

                create_work_item(
                    engine,
                    title=issue["title"],
                    repo_name=repo_name,
                    description=issue.get("description"),
                    created_by="legacy-migration",
                )
                item_count += 1
            except (json.JSONDecodeError, KeyError, IOError) as e:
                console.print(f"[yellow]Warning: skipping {issue_file.name}: {e}[/yellow]")

    # --- Migrate task_lists/*.json --------------------------------------------
    tasks_dir = Path(LEGACY_TASK_LISTS_DIR)
    if tasks_dir.is_dir():
        for task_file in sorted(tasks_dir.glob("*.json")):
            try:
                data = json.loads(task_file.read_text())
                for task in data.get("tasks", []):
                    pri_raw = task.get("priority", "medium").lower()
                    try:
                        pri = Priority(pri_raw)
                    except ValueError:
                        pri = Priority.medium

                    create_work_item(
                        engine,
                        title=task.get("subject", task.get("title", "Untitled")),
                        description=task.get("description"),
                        priority=pri,
                        created_by="legacy-migration",
                    )
                    item_count += 1
            except (json.JSONDecodeError, IOError) as e:
                console.print(f"[yellow]Warning: skipping {task_file.name}: {e}[/yellow]")

    console.print(f"[green]Migration complete:[/green] {repo_count} repos, {item_count} work items imported.")
