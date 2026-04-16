"""Centralized configuration for ForgeOps."""

import os
from pathlib import Path

# Base directory — defaults to current working directory, overridable via env var.
BASE_DIR = Path(os.environ.get("FORGEOPS_BASE_DIR", "."))

# API server
API_HOST = os.environ.get("FORGEOPS_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("FORGEOPS_API_PORT", "8002"))

# SQLite database path
DB_PATH = Path(os.environ.get("FORGEOPS_DB_PATH", str(BASE_DIR / "forgeops.db")))

# Legacy paths (used only during migration)
LEGACY_ISSUES_DIR = BASE_DIR / "issues"
LEGACY_COUNTER_FILE = BASE_DIR / "issue_counter.txt"
LEGACY_REPOS_FILE = BASE_DIR / "repos.json"
LEGACY_TASK_LISTS_DIR = BASE_DIR / "task_lists"
