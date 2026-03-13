# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ForgeOps is a cross-repo work ledger for AI-assisted software development. It tracks issues, tasks, assignments, and progress so that work remains organized, reviewable, and resumable across sessions and repositories. See `docs/PURPOSE.md` for scope boundaries and `docs/VISION.md` for long-term direction.

The codebase is a Python CLI + REST API backed by SQLite via SQLModel. Phase 1 (Unified Foundation) is complete — all data lives in a single SQLite database with Pydantic/SQLModel models. See `docs/ARCHITECTURE.md` for full architecture and `docs/ROADMAP.md` for the build plan.

## Commands

### Running the CLI
```bash
uv run python main.py <command>
```
Available commands: `create-issue`, `list-issues`, `view-issue`, `list-repos`, `add-repo`, `update-repo`, `remove-repo`, `migrate-issues`. Run `uv run python main.py --help` for full help.

Key options:
- `list-issues --repo <name> --state <state> --blocked`
- `add-repo <name> --org <org> --branch <branch> --url <url> --description <desc>`
- `update-repo <name> --org <org> --branch <branch> --status active|archived --url <url> --description <desc>`
- `list-repos --all` (includes archived)
- `view-issue WI-<n>` or `view-issue <n>`

### Running the API
```bash
uv run uvicorn api:app --reload
```
Serves at `http://localhost:8000`. Endpoints: `GET /issues`, `GET /repositories`, docs at `/docs`. No authentication.

### Running Tests
```bash
uv run python -m pytest tests/ -v
# Single test:
uv run python -m pytest tests/test_database.py::TestDatabaseLayer::test_create_and_get_work_item -v
```
Tests use `unittest.TestCase` style. Install test deps with `uv sync --extra test`.

### Dependencies
Managed with `uv` (lock file: `uv.lock`). Python 3.13+ required.
```bash
uv sync
```
Runtime: FastAPI, SQLModel (includes SQLAlchemy + Pydantic), Rich, Typer, uvicorn.

## Architecture

**Key files:**
- `models.py` — SQLModel/Pydantic models for all 5 core objects (Repository, WorkItem, Assignment, ExecutionRecord, Review) plus enums
- `config.py` — Centralized configuration with env var support (`FORGEOPS_DB_PATH`, `FORGEOPS_BASE_DIR`)
- `core/database.py` — SQLModel data access layer (single source of truth)
- `core/repository_manager.py` — Repository validation and management
- `commands/` — CLI command handlers (one per file)
- `api.py` — FastAPI REST endpoints

**Data flows through SQLite only.** No JSON files. The `migrate-issues` command imports legacy JSON data into the new schema.

See `docs/ARCHITECTURE.md` for the complete architecture document including:
- Target data model (five core objects)
- State engine (8-state lifecycle, block mechanism, repo concurrency guard)
- Roadmap mapping

## Development Workflow

- **Branch policy:** All work happens on `main`. Do not create feature branches.
- **Commits:** Commit as you complete tasks and make progress through `docs/ROADMAP.md`. Each commit should be a meaningful unit of work with a clear message. Update the ROADMAP checkboxes when items are completed, including the date and commit hash.
- **Roadmap:** `docs/ROADMAP.md` is the build plan. It defines the core data objects, state engine, and phased delivery. Refer to it before starting new work.
- `create-issue` is interactive (prompts via `input()`) — it cannot be used non-interactively without modification.
- **`.gitignore` hygiene:** Whenever you create, modify, or encounter a file or folder that is sensitive (credentials, secrets, `.env`, API keys, tokens), generated at runtime (databases, logs, caches, build artifacts), or produced by a script — **update `.gitignore` immediately** before committing. If a sensitive file is already tracked, remove it from tracking with `git rm --cached`. This is a security requirement, not optional.

## Notes

- The project name in `pyproject.toml` is still `jules-dev-kit` (the original name before rename to ForgeOps).
- No CI/CD, linter, or formatter configured. The roadmap plans ruff, mypy, and GitHub Actions.
- Legacy files (`issues/`, `repos.json`, `issue_counter.txt`, `task_lists/`) still exist on disk but are no longer read by any code path except the migration command.
