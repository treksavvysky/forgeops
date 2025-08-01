"""Migrate existing issue JSON files into the SQLite database."""

from core.file_manager import FileManager
from core.db import Database


def migrate_issues() -> None:
    fm = FileManager()
    db = Database()
    issues = fm.load_all_issues()
    if not issues:
        print("No issues found to migrate.")
        return
    for issue in issues:
        db.add_issue(issue)
        db.add_repository(issue["repository"])
    print(f"Migrated {len(issues)} issue(s) into {db.db_path}.")
