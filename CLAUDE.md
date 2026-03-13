# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ForgeOps is a cross-repo work ledger for AI-assisted software development. It tracks issues, tasks, assignments, and progress so that work remains organized, reviewable, and resumable across sessions and repositories. See `docs/PURPOSE.md` for scope boundaries and `docs/VISION.md` for long-term direction.

The current codebase is a Python CLI issue tracker with SQLite storage and a FastAPI REST API — the foundation that the roadmap builds on. See `docs/ARCHITECTURE.md` for the full current architecture, target data model, and state engine design.

## Commands

### Running the CLI
```bash
uv run python main.py <command>
```
Available commands: `create-issue`, `list-issues`, `list-issues --repo <name>`, `view-issue <ISSUE-ID>`, `list-repos`, `add-repo <repo-name>`, `migrate-issues`. Run `uv run python main.py --help` for full help.

### Running the API
```bash
uv run uvicorn api:app --reload
```
Serves at `http://localhost:8000`. Endpoints: `GET /issues`, docs at `/docs`. No authentication.

### Running Tests
```bash
uv run python -m pytest tests/ -v
# Single test:
uv run python -m pytest tests/test_task_manager.py::TestTaskManager::test_add_task -v
```
Tests use `unittest.TestCase` style. Install test deps with `uv sync --extra test`.

### Dependencies
Managed with `uv` (lock file: `uv.lock`). Python 3.13+ required.
```bash
uv sync
```

## Architecture

See `docs/ARCHITECTURE.md` for the complete architecture document including:
- Current three-layer design (commands → core → utils)
- Dual storage model (JSON files + SQLite) and its limitations
- Target data model (five core objects: Repository, Work Item, Assignment, Execution Record, Review)
- State engine (8-state lifecycle, block mechanism, repo concurrency guard)
- Roadmap mapping (what exists today vs. what each phase changes)

## Development Workflow

- **Branch policy:** All work happens on `main`. Do not create feature branches.
- **Commits:** Commit as you complete tasks and make progress through `docs/ROADMAP.md`. Each commit should be a meaningful unit of work with a clear message. Update the ROADMAP checkboxes when items are completed, including the date and commit hash.
- **Roadmap:** `docs/ROADMAP.md` is the build plan. It defines the core data objects, state engine, and phased delivery. Refer to it before starting new work.
- `create-issue` is interactive (prompts via `input()`) — it cannot be used non-interactively without modification.

## Notes

- The project name in `pyproject.toml` is still `jules-dev-kit` (the original name before rename to ForgeOps).
- No CI/CD, linter, or formatter configured. The roadmap plans ruff, mypy, and GitHub Actions.
