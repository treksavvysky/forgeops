# ForgeOps Architecture

This document describes the current architecture of ForgeOps and how it maps to the roadmap's target state.

---

## System Purpose

ForgeOps is the work-tracking ledger for AI-assisted development. It records what work exists, what state it's in, who or what is responsible, and what outcomes were produced — so that development remains organized and resumable across sessions, repositories, and agents.

See [PURPOSE.md](PURPOSE.md) for full scope boundaries. See [ROADMAP.md](ROADMAP.md) for the build plan.

---

## Current Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────┐
│  Interfaces                                     │
│  ┌──────────────┐  ┌────────────────────────┐   │
│  │  CLI (Typer)  │  │  REST API (FastAPI)    │   │
│  │  main.py      │  │  api.py                │   │
│  └──────┬───────┘  └───────────┬────────────┘   │
├─────────┼──────────────────────┼────────────────┤
│  Commands / Handlers           │                 │
│  ┌──────┴───────┐              │                 │
│  │  commands/    │              │                 │
│  │  create_issue │              │                 │
│  │  list_issues  │              │                 │
│  │  view_issue   │              │                 │
│  │  list_repos   │              │                 │
│  │  add_repo     │              │                 │
│  │  migrate_issues│             │                 │
│  └──────┬───────┘              │                 │
├─────────┼──────────────────────┼────────────────┤
│  Core Business Logic           │                 │
│  ┌─────────────────────────────┴──────────────┐ │
│  │  IssueTracker    — creation orchestration   │ │
│  │  FileManager     — JSON file I/O, ID gen    │ │
│  │  RepositoryManager — repo registry + valid. │ │
│  │  TaskManager     — task lists (standalone)  │ │
│  │  Database        — SQLite wrapper           │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  utils/                                      │ │
│  │  InputValidator — interactive input + valid. │ │
│  │  helpers        — format_datetime, truncate  │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Storage Model

ForgeOps currently uses **dual storage** — JSON files and SQLite — that are **not automatically synchronized**.

```
                    CLI writes here              API reads here
                         │                            │
                         ▼                            ▼
              ┌──────────────────┐         ┌──────────────────┐
              │  issues/*.json   │ ──────► │   forgeops.db    │
              │  issue_counter   │ migrate │   (SQLite)       │
              │  repos.json      │ ──────► │                  │
              └──────────────────┘         └──────────────────┘
```

| Storage | Used by | Source of truth for |
|---------|---------|---------------------|
| `issues/ISSUE-NNN.json` | CLI (read/write) | Issue content |
| `issue_counter.txt` | FileManager | Next issue ID |
| `repos.json` | RepositoryManager | Repository names |
| `forgeops.db` | API (read), migration (write) | Nothing — populated by `migrate-issues` |
| `task_lists/*.json` | TaskManager | Task lists (separate system) |

**Key limitation:** Creating an issue via CLI writes to JSON but the API won't see it until `migrate-issues` is run. The ROADMAP Phase 1 eliminates this by moving to SQLite as the single source of truth.

### Data Schemas

**Issue (JSON file)**
```json
{
  "id": "ISSUE-001",
  "title": "string",
  "description": "string",
  "repository": "string",
  "created_at": "ISO 8601 timestamp"
}
```

**SQLite — `repositories` table**
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | UNIQUE NOT NULL |

**SQLite — `issues` table**
| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| title | TEXT | NOT NULL |
| description | TEXT | nullable |
| repository | TEXT | NOT NULL, FK → repositories.name |
| created_at | TEXT | NOT NULL |

**Task list (JSON file)**
```json
{
  "version": "1.0.0",
  "name": "list_name",
  "association": "project-name",
  "created_by": "username",
  "created_on": "ISO 8601",
  "tasks": [
    {
      "task_id": "UUID",
      "subject": "string",
      "description": "string",
      "status": "open | in_progress | closed",
      "priority": "low | medium | high",
      "date_created": "ISO 8601",
      "comments": [{ "comment": "string", "timestamp": "ISO 8601" }]
    }
  ]
}
```

### Data Flow

**Create issue** (the most complex flow):
```
User → CLI prompt
  → InputValidator (title, repo, description)
  → RepositoryManager.validate_repo_name()
  → RepositoryManager.suggest_repositories() (on mismatch)
  → IssueTracker.confirm_repository() (interactive)
  → FileManager.get_next_issue_id() (reads/increments issue_counter.txt)
  → IssueTracker.display_issue_preview()
  → User confirms
  → FileManager.save_issue() (writes issues/ISSUE-NNN.json)
  → Database.add_issue() (upserts to SQLite)
  → Database.add_repository() (upserts to SQLite)
```

**List/view issues**: FileManager reads from `issues/*.json`. No SQLite involved.

**API**: Database reads from SQLite. No JSON files involved.

**Migration**: FileManager reads all JSON → Database writes to SQLite. One-way, re-runnable (upserts).

### Two Disconnected Systems

Issues and tasks are **separate and unlinked**:

| Aspect | Issues | Tasks |
|--------|--------|-------|
| Storage | `issues/*.json` + SQLite | `task_lists/*.json` |
| ID format | `ISSUE-NNN` (sequential) | UUID |
| CLI access | Yes (6 commands) | None |
| API access | Yes (`GET /issues`) | None |
| Metadata | title, description, repo, created_at | subject, description, priority, status, comments |
| Manager | IssueTracker + FileManager | TaskManager |

The ROADMAP Phase 1 unifies these into a single `work_items` table.

---

## Import Graph

```
main.py
  ├── commands/create_issue  → core/issue_tracker → db, repository_manager,
  │                                                  file_manager, validators
  ├── commands/list_issues   → core/file_manager, utils/helpers
  ├── commands/view_issue    → core/file_manager, utils/helpers
  ├── commands/list_repos    → core/repository_manager
  ├── commands/add_repo      → core/repository_manager
  └── commands/migrate_issues → core/file_manager, core/db

api.py → core/db
```

TaskManager has **no callers** in the current codebase — it exists as library code only.

---

## Interfaces

### CLI (`main.py`)

Typer-based with 6 commands. Interactive input via `InputValidator`. No batch/scriptable mode for `create-issue`.

| Command | Args/Options | Reads from | Writes to |
|---------|-------------|------------|-----------|
| `create-issue` | (interactive) | repos.json, issue_counter.txt | issues/*.json, forgeops.db |
| `list-issues` | `--repo <name>` | issues/*.json | — |
| `view-issue` | `<ISSUE-ID>` | issues/*.json | — |
| `list-repos` | — | repos.json | — |
| `add-repo` | `<repo-name>` | repos.json | repos.json, forgeops.db |
| `migrate-issues` | — | issues/*.json | forgeops.db |

### REST API (`api.py`)

Single endpoint. No authentication. Reads from SQLite only.

| Endpoint | Method | Response |
|----------|--------|----------|
| `/issues` | GET | `List[Dict]` — all issues from SQLite |
| `/docs` | GET | Auto-generated OpenAPI docs |

---

## Dependencies

**Runtime:** Python 3.13+, FastAPI, Typer, uvicorn
**Test:** pytest, datetime-truncate
**Package manager:** uv

No ORM, no migrations framework, no linter/formatter configured. All database access is raw `sqlite3`.

---

## Mapping to Roadmap

### What exists today

| Roadmap capability | Current state | Where in code |
|--------------------|---------------|---------------|
| Repositories | Name registry, format validation, suggestions | `RepositoryManager`, `repos.json` |
| Issues | CRUD via CLI, JSON storage, SQLite mirror | `IssueTracker`, `FileManager`, `Database` |
| Tasks | Standalone JSON-based system, no CLI | `TaskManager`, `task_lists/` |
| Assignments | Not implemented | — |
| Progress states | Tasks have free-text status; issues have none | `TaskManager.update_task()` |
| Artifacts | Not implemented | — |
| Reviews | Not implemented | — |
| Session continuity | Not implemented | — |

### Phase 1 changes to this architecture

The most significant architectural change is **retiring dual storage**. After Phase 1:

- `issues/*.json`, `issue_counter.txt`, `repos.json`, `task_lists/*.json` are replaced by SQLite via SQLModel
- `FileManager` and `TaskManager` are retired
- Issues and tasks merge into a single `work_items` table with Pydantic validation
- All interfaces (CLI, API) read/write through the same data layer
- Hardcoded paths move to `config.py` with environment variable support

### Phase 2 additions to this architecture

New core modules for:
- State machine (allowed transitions between work item statuses)
- Assignment tracking (who/what is responsible, ownership history)
- Session snapshots (work-state capture and resume)
- Review queue (AI-generated code awaiting human inspection)
- Artifacts (links between work items and external references)
- Task hierarchy (parent-child relationships, progress rollup)

### Phase 3 additions to this architecture

- Full CRUD REST API replacing the current single-endpoint `api.py`
- Authentication layer (bearer token / API key)
- Ecosystem hooks (JCT integration, event bus, MCP server)
- The three-layer design remains, but the interface layer expands significantly
