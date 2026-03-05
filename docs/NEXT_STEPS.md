# Next Steps

Improvements to tackle after the current round of bug fixes and cleanup.

---

## 1. Add Test Coverage for Commands and Core Modules

Only `TaskManager` has tests today (`tests/test_task_manager.py`). The following modules have zero test coverage and should be prioritized:

- **`FileManager`** — test `get_next_issue_id()` counter logic, `save_issue()`/`load_issue()` round-tripping, and `load_all_issues()` ordering.
- **`RepositoryManager`** — test `validate_repo_name()` edge cases, `suggest_repositories()` matching, and `add_repository()` deduplication.
- **`Database`** — test schema creation, `add_issue()`/`get_issues()` round-tripping, and `add_repository()` uniqueness constraint.
- **CLI commands** — integration tests that invoke `create_issue`, `list_issues`, `view_issue` with mocked stdin/stdout.

Prerequisites:
- Add `pytest` and `datetime-truncate` to `pyproject.toml` under `[project.optional-dependencies]` or a `[tool.pytest]` dev group.

---

## 2. Replace `datetime.utcnow()` with `datetime.now(datetime.UTC)`

`datetime.utcnow()` is deprecated since Python 3.12 and ForgeOps requires Python 3.13+. All occurrences should be replaced:

- `commands/create_issue.py` — issue `created_at` timestamp
- `core/task_manager.py` — task `date_created` and comment `timestamp`

Use `from datetime import datetime, UTC` and call `datetime.now(UTC)`.

---

## 3. Handle Corrupt TaskManager State

In `core/task_manager.py`, when `_load_task_list()` encounters a corrupt JSON file, it sets `self.task_data = None`. Any subsequent call to `add_task()` or `add_comment_to_task()` will crash with `TypeError: 'NoneType' object is not subscriptable`.

Fix: when the JSON file is unreadable, either re-initialize `task_data` with an empty task list structure (and log a warning), or raise an explicit error during `__init__` so the caller knows the file is broken.

---

## 4. Migrate CLI to Typer or Click

The `sys.argv` parsing in `main.py` is manual and will become harder to maintain as commands grow. Migrating to [Typer](https://typer.tiangolo.com/) would provide:

- Automatic `--help` generation per command
- Argument type validation and error messages
- Shell completion for repository names (roadmap item)
- Subcommand grouping (issue commands vs repo commands vs task commands)

This aligns with the Phase 1 "Modern CLI Framework" item in `ROADMAP.md`.
