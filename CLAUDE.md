# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ForgeOps is a Python CLI issue tracking system with SQLite storage and a FastAPI REST API. It manages issues and repositories through an interactive command-line interface. The project uses dual storage: individual JSON files per issue (`issues/`) and a SQLite database (`forgeops.db`), with a migration command to sync between them.

## Commands

### Running the CLI
```bash
uv run python main.py <command>
```

Available commands: `create-issue`, `list-issues`, `list-issues --repo <name>`, `view-issue <ISSUE-ID>`, `list-repos`, `add-repo <repo-name>`, `migrate-issues`, `help`

### Running the API
```bash
uv run uvicorn api:app --reload
```
Serves at `http://localhost:8000`. Endpoints: `GET /issues`, docs at `/docs`. No authentication — the API is open.

### Running Tests
```bash
uv run python -m pytest tests/ -v
# Single test:
uv run python -m pytest tests/test_task_manager.py::TestTaskManager::test_add_task -v
```

### Dependencies
Managed with `uv` (lock file: `uv.lock`). Python 3.13+ required.
```bash
uv sync
```

## Architecture

**CLI routing**: `main.py` parses `sys.argv` and dispatches to handler functions in `commands/`. There is no CLI framework — commands are matched via if/elif chains.

**Three-layer structure**:
- `commands/` — CLI command handlers (user interaction, argument handling)
- `core/` — Business logic (IssueTracker, FileManager, RepositoryManager, TaskManager, Database)
- `utils/` — Input validation (`validators.py`) and formatting helpers (`helpers.py`)

**Dual storage model**: Issues exist as individual JSON files in `issues/` AND in SQLite (`forgeops.db`). These are not automatically synced — `migrate-issues` imports JSON files into SQLite. The API reads from SQLite only. New issues created via CLI write to JSON files and increment `issue_counter.txt`.

**Database schema** (`core/db.py`): Two tables — `repositories` (id, name) and `issues` (id, title, description, repository FK, created_at). Raw sqlite3 queries, no ORM.

**Repository registry**: `repos.json` holds the list of valid repository names. The RepositoryManager validates repo names against this list and suggests similar names on mismatch.

**Task lists**: `core/task_manager.py` manages JSON-based task lists in `task_lists/`, separate from the issue system. Not yet integrated into the CLI.

## Key Files

- `main.py` — CLI entry point and command router
- `api.py` — FastAPI app with GET /issues endpoint
- `core/db.py` — SQLite wrapper, schema creation, CRUD
- `core/issue_tracker.py` — Issue creation orchestration with repo validation
- `core/file_manager.py` — JSON file I/O, issue ID generation (ISSUE-NNN format)
- `core/repository_manager.py` — Repo registry management, name validation
- `repos.json` — Repository name registry
- `issue_counter.txt` — Next issue ID counter

## Notes

- The project name in `pyproject.toml` is still `jules-dev-kit` (the original name before rename to ForgeOps).
- No CI/CD, linter, or formatter configured. The roadmap (`docs/ROADMAP.md`) plans ruff, mypy, and GitHub Actions.
- Test coverage is limited to `TaskManager` only (`tests/test_task_manager.py`). Tests use `unittest.TestCase` style (not pytest fixtures). No tests exist for commands or core issue/repo logic.
- `pytest` and `datetime-truncate` are test dependencies but neither is declared in `pyproject.toml` — they must be available in the `uv` environment.
- `create-issue` is interactive (prompts for input via `input()`) — it cannot be used non-interactively without modification.
