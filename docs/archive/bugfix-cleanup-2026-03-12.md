# Bugfix & Cleanup Sprint — Completed 2026-03-12

Improvements tackled after the initial round of bug fixes and cleanup.

---

## 1. Add Test Coverage for Commands and Core Modules

**Commit:** `0ced06b` — `test: add test coverage for FileManager, RepositoryManager, Database, and CLI commands`

Added 44 new tests across 4 test files:
- `tests/test_file_manager.py` — counter logic, save/load round-trip, load_all sorting
- `tests/test_repository_manager.py` — name validation, suggestions, add/dedup, DB sync
- `tests/test_db.py` — schema creation, repo/issue CRUD, upsert, context manager
- `tests/test_commands.py` — list-issues, view-issue, list-repos, add-repo, migrate-issues

Declared `pytest` and `datetime-truncate` as test dependencies in `pyproject.toml`.

---

## 2. Replace `datetime.utcnow()` with `datetime.now(UTC)`

**Commit:** `015bdc2` — `fix: replace deprecated datetime.utcnow() with datetime.now(UTC)`

Updated all occurrences in:
- `commands/create_issue.py`
- `core/task_manager.py`
- `tests/test_task_manager.py`

Eliminated all deprecation warnings from the test suite.

---

## 3. Handle Corrupt TaskManager State

**Commit:** `77d0b69` — `fix: raise explicit error on corrupt TaskManager JSON instead of setting None`

`_load_task_list()` now raises `RuntimeError` with the file path and parse error details on corrupt JSON or I/O failures, instead of silently setting `task_data = None`. Added test for the behavior.

---

## 4. Migrate CLI to Typer

**Commit:** `218b783` — `refactor: migrate CLI from sys.argv parsing to Typer`

Replaced manual if/elif command dispatch in `main.py` with Typer subcommands. Provides auto-generated `--help` for all commands, argument type validation, and shell completion via `--install-completion`. Command handler functions in `commands/` unchanged.
