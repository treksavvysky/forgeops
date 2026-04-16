# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ForgeOps is a cross-repo work ledger for AI-assisted software development. It tracks issues, tasks, assignments, and progress so that work remains organized, reviewable, and resumable across sessions and repositories. See `docs/PURPOSE.md` for scope boundaries and `docs/VISION.md` for long-term direction.

The codebase is a Python CLI + REST API backed by SQLite via SQLModel. Phases 1-3 (Unified Foundation, Work Ledger, API & Ecosystem) are largely complete — all data lives in a single SQLite database with Pydantic/SQLModel models. The CLI has 27 commands, the API has full CRUD with bearer token auth, and the event hook system fires on all state engine operations. See `docs/ARCHITECTURE.md` for full architecture and `docs/ROADMAP.md` for the build plan.

## Commands

### Running the CLI
```bash
uv run python main.py <command>
```
27 commands across 8 categories. Run `uv run python main.py --help` for full list.

Key commands:
- **Work items:** `create-issue`, `list-issues`, `view-issue`
- **State engine:** `update-status <ID> --state <state>`, `block <ID> --reason "..."`, `unblock <ID>`
- **Assignments:** `assign <ID> <executor> --type human|agent`, `my-issues <executor>`, `agent-tasks <executor>`
- **Execution:** `log-run <ID> --executor --status`, `runs <ID>`
- **Reviews:** `review-queue`, `approve <ID> --reviewer`, `request-changes <ID> --reviewer`
- **Session:** `status`, `next`, `snapshot`, `resume`
- **Attachments:** `attach <ID> <url>`, `list-attachments <ID>`
- **Tasks:** `add-task <parent-ID> <title>`, `list-tasks <parent-ID>`
- **Repos:** `list-repos`, `add-repo`, `update-repo`, `remove-repo`
- **Migration:** `migrate-issues`

### Running the API
```bash
uv run uvicorn api:app --reload --host 127.0.0.1 --port 8002
```

Serves at `http://localhost:8002`. Full CRUD API — docs at `/docs`. Auth via `API_BEARER_TOKEN` env var (skipped if unset). Port configurable via `FORGEOPS_API_PORT` (default 8002).

### Running the MCP Server
```bash
uv run python mcp_server.py
```
Stdio transport — 19 tools for full ledger CRUD. For Claude Code integration, add to `.claude/settings.local.json`.

### Running Tests
```bash
uv run python -m pytest tests/ -v
# Single test:
uv run python -m pytest tests/test_database.py::TestDatabaseLayer::test_create_and_get_work_item -v
```
Tests use `unittest.TestCase` style. Install test deps with `uv sync --extra test`.

### Linting & Type Checking
```bash
uv run ruff check .           # Lint
uv run ruff format --check .  # Format check
uv run mypy *.py core/ commands/  # Type check
```
All three run in CI (`.github/workflows/ci.yml`) on every push to `main`.

### Dependencies
Managed with `uv` (lock file: `uv.lock`). Python 3.13+ required.
```bash
uv sync
```
Runtime: FastAPI, SQLModel (includes SQLAlchemy + Pydantic), Rich, Typer, uvicorn.

## Architecture

**Key files:**
- `models.py` — SQLModel/Pydantic models for 7 tables (Repository, WorkItem, Assignment, ExecutionRecord, Review, ActivityLog, Attachment) plus enums
- `config.py` — Centralized configuration with env var support (`FORGEOPS_DB_PATH`, `FORGEOPS_BASE_DIR`)
- `core/database.py` — SQLModel data access layer (single source of truth)
- `core/state_engine.py` — Transition validation and repo concurrency guard
- `core/hooks.py` — Event hook system (7 events, subscribe/fire pattern)
- `core/repository_manager.py` — Repository validation and management
- `commands/` — CLI command handlers (one per file, 14 modules)
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
