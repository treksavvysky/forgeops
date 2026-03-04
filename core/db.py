import sqlite3
from pathlib import Path
from typing import List, Dict


class Database:
    """Simple SQLite wrapper for issues and repositories."""

    def __init__(self, db_path: str = "forgeops.db") -> None:
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                repository TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(repository) REFERENCES repositories(name)
            )
            """
        )
        self.conn.commit()

    def add_repository(self, name: str) -> None:
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO repositories(name) VALUES (?)", (name,))
        self.conn.commit()

    def get_repositories(self) -> List[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM repositories ORDER BY name")
        return [row[0] for row in cur.fetchall()]

    def add_issue(self, issue_data: Dict[str, str]) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO issues (id, title, description, repository, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                issue_data["id"],
                issue_data["title"],
                issue_data.get("description"),
                issue_data["repository"],
                issue_data["created_at"],
            ),
        )
        self.conn.commit()

    def get_issues(self) -> List[Dict[str, str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, title, description, repository, created_at FROM issues ORDER BY id")
        return [dict(row) for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
