# ForgeOps Architecture

This document describes the current architecture of ForgeOps and how it maps to the roadmap's target state.

---

## System Purpose

ForgeOps is the work-tracking ledger for AI-assisted development. It records what work exists, what state it's in, who or what is responsible, and what outcomes were produced — so that development remains organized and resumable across sessions, repositories, and agents.

See [PURPOSE.md](PURPOSE.md) for full scope boundaries. See [ROADMAP.md](ROADMAP.md) for the build plan.

---

## Current Architecture

*Updated after Phase 3 (API & Hooks) completion (2026-03-13).*

### Three-Layer Design

```
┌──────────────────────────────────────────────────────┐
│  Interfaces                                          │
│  ┌──────────────┐  ┌────────────────────────┐        │
│  │  CLI (Typer)  │  │  REST API (FastAPI)    │        │
│  │  main.py      │  │  api.py                │        │
│  └──────┬───────┘  └───────────┬────────────┘        │
├─────────┼──────────────────────┼─────────────────────┤
│  Commands / Handlers           │                      │
│  ┌──────┴───────┐              │                      │
│  │  commands/    │              │                      │
│  │  create_issue │  state       │                      │
│  │  list_issues  │  assign      │                      │
│  │  view_issue   │  execution   │                      │
│  │  list_repos   │  review      │                      │
│  │  add_repo     │  session     │                      │
│  │  update_repo  │  attachments │                      │
│  │  remove_repo  │  tasks       │                      │
│  │  migrate_issues│             │                      │
│  └──────┬───────┘              │                      │
├─────────┼──────────────────────┼─────────────────────┤
│  Core                          │                      │
│  ┌─────────────────────────────┴───────────────────┐ │
│  │  database.py        — SQLModel data access layer │ │
│  │  state_engine.py    — transitions + concurrency  │ │
│  │  hooks.py           — event hook registry        │ │
│  │  repository_manager — repo validation + CRUD     │ │
│  └──────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │  models.py  — SQLModel models + Pydantic enums   │ │
│  │  config.py  — Centralized config (env vars)      │ │
│  └──────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │  utils/                                           │ │
│  │  InputValidator — interactive input + validation  │ │
│  │  helpers        — format_datetime, truncate       │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### Storage Model

ForgeOps uses a **single SQLite database** as the sole source of truth. Both CLI and API read/write the same database through the SQLModel data access layer.

```
              CLI                    API
               │                      │
               ▼                      ▼
        ┌─────────────────────────────────┐
        │  core/database.py (SQLModel)    │
        │         ↕                       │
        │  forgeops.db (SQLite)           │
        │  ┌────────────────────────────┐ │
        │  │  repositories              │ │
        │  │  work_items                │ │
        │  │  assignments               │ │
        │  │  execution_records          │ │
        │  │  reviews                    │ │
        │  │  activity_log               │ │
        │  │  attachments                │ │
        │  └────────────────────────────┘ │
        └─────────────────────────────────┘
```

Legacy JSON files (`issues/`, `repos.json`, `issue_counter.txt`, `task_lists/`) still exist on disk but are only read by the `migrate-issues` command.

### Data Schemas

All models defined in `models.py` using SQLModel (Pydantic + SQLAlchemy).

**`repositories` table**
| Column | Type | Constraints |
|--------|------|-------------|
| repo_id | INTEGER | PRIMARY KEY |
| name | TEXT | UNIQUE, indexed |
| org | TEXT | nullable |
| default_branch | TEXT | nullable |
| status | TEXT | "active" / "archived", default "active" |
| url | TEXT | nullable |
| description | TEXT | nullable |

**`work_items` table**
| Column | Type | Constraints |
|--------|------|-------------|
| task_id | INTEGER | PRIMARY KEY |
| repo_id | INTEGER | FK → repositories.repo_id, indexed |
| title | TEXT | NOT NULL |
| description | TEXT | nullable |
| state | TEXT | enum (8 states), default "queued", indexed |
| priority | TEXT | enum (low/medium/high/urgent), default "medium" |
| is_blocked | BOOLEAN | default false |
| blocked_reason | TEXT | nullable |
| parent_id | INTEGER | FK → work_items.task_id (self-referential) |
| created_by | TEXT | nullable |
| created_at | DATETIME | auto-set |
| updated_at | DATETIME | auto-updated |

**`activity_log` table**
| Column | Type | Constraints |
|--------|------|-------------|
| log_id | INTEGER | PRIMARY KEY |
| task_id | INTEGER | FK → work_items.task_id, nullable, indexed |
| action | TEXT | enum (state_change, blocked, unblocked, assigned, comment, created, review_submitted, execution_logged) |
| detail | TEXT | nullable |
| actor | TEXT | nullable |
| created_at | DATETIME | auto-set |

**`attachments` table**
| Column | Type | Constraints |
|--------|------|-------------|
| attachment_id | INTEGER | PRIMARY KEY |
| task_id | INTEGER | FK → work_items.task_id, indexed |
| url_or_path | TEXT | NOT NULL |
| label | TEXT | nullable |
| created_at | DATETIME | auto-set |

**`assignments` table**
| Column | Type | Constraints |
|--------|------|-------------|
| assignment_id | INTEGER | PRIMARY KEY |
| task_id | INTEGER | FK → work_items.task_id |
| executor | TEXT | NOT NULL |
| executor_type | TEXT | "human" / "agent" |
| assigned_at | DATETIME | auto-set |

**`execution_records` table** | Column | Type | Constraints |
|--------|------|-------------|
| run_id | INTEGER | PRIMARY KEY |
| task_id | INTEGER | FK → work_items.task_id |
| executor | TEXT | NOT NULL |
| branch | TEXT | nullable |
| commit | TEXT | nullable |
| status | TEXT | "success" / "failed" / "partial" |
| logs_ref | TEXT | nullable |
| artifact_ref | TEXT | nullable |
| created_at | DATETIME | auto-set |

**`reviews` table** | Column | Type | Constraints |
|--------|------|-------------|
| review_id | INTEGER | PRIMARY KEY |
| task_id | INTEGER | FK → work_items.task_id |
| reviewer | TEXT | NOT NULL |
| decision | TEXT | "accepted" / "rework_required" |
| note | TEXT | nullable |
| created_at | DATETIME | auto-set |

### Data Flow

**Create work item** (interactive):
```
User → CLI prompt
  → InputValidator (title, repo, description)
  → RepositoryManager.validate_repo_name()
  → RepositoryManager.suggest_repositories() (on mismatch)
  → _confirm_repository() (interactive)
  → Preview (Rich Panel)
  → User confirms
  → database.add_repository() (ensure repo exists)
  → database.create_work_item() (writes to SQLite)
```

**List/view work items**: `database.list_work_items()` / `database.get_work_item()` — reads from SQLite with eager-loaded relationships.

**API**: Same `database.*` functions, same SQLite. CLI and API always see the same data.

**Migration**: `migrate-issues` reads legacy JSON files and calls `database.create_work_item()` for each.

---

## Import Graph

```
main.py
  ├── commands/create_issue   → core/database, core/repository_manager, utils/validators
  ├── commands/list_issues    → core/database, models
  ├── commands/view_issue     → core/database
  ├── commands/state          → core/database, core/state_engine
  ├── commands/assign         → core/database
  ├── commands/execution      → core/database
  ├── commands/review         → core/database, core/state_engine
  ├── commands/session        → core/database, config
  ├── commands/attachments    → core/database
  ├── commands/tasks          → core/database
  ├── commands/list_repos     → core/database
  ├── commands/add_repo       → core/database, core/repository_manager
  ├── commands/update_repo    → core/database, core/repository_manager
  ├── commands/remove_repo    → core/database, core/repository_manager
  └── commands/migrate_issues → core/database, config

api.py → core/database, models
```

---

## Interfaces

### CLI (`main.py`)

Typer-based with 27 commands. Rich output for tables and panels. Interactive input via `InputValidator`. Repository autocompletion on `--repo`.

| Command | Args/Options | Category |
|---------|-------------|----------|
| `create-issue` | `--priority`, `--created-by` (interactive) | Work Items |
| `list-issues` | `--repo`, `--state`, `--blocked`, `--priority` | Work Items |
| `view-issue` | `WI-<n>` or `<n>` | Work Items |
| `update-status` | `<ID> --state <state>` | State Engine |
| `block` | `<ID> --reason "..."` | State Engine |
| `unblock` | `<ID>` | State Engine |
| `assign` | `<ID> <executor> --type human\|agent` | Assignments |
| `my-issues` | `<executor>` | Assignments |
| `agent-tasks` | `<executor>` | Assignments |
| `log-run` | `<ID> --executor --status [--branch --commit]` | Execution |
| `runs` | `<ID>` | Execution |
| `review-queue` | — | Reviews |
| `approve` | `<ID> --reviewer [--note]` | Reviews |
| `request-changes` | `<ID> --reviewer [--note]` | Reviews |
| `status` | — | Session |
| `next` | — | Session |
| `snapshot` | — | Session |
| `resume` | — | Session |
| `attach` | `<ID> <url-or-path> [--label]` | Attachments |
| `list-attachments` | `<ID>` | Attachments |
| `add-task` | `<parent-ID> <title>` | Task Hierarchy |
| `list-tasks` | `<parent-ID>` | Task Hierarchy |
| `list-repos` | `--all` | Repositories |
| `add-repo` | `<name> [--org --branch --url --description]` | Repositories |
| `update-repo` | `<name> [--org --branch --status --url --description]` | Repositories |
| `remove-repo` | `<name>` | Repositories |
| `migrate-issues` | — | Migration |

### REST API (`api.py`)

Full CRUD API with bearer token auth (via `API_BEARER_TOKEN` env var, skipped if unset). Default port 8002 (configurable via `FORGEOPS_API_PORT`).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/work-items` | GET | List work items (filter: repo, state, priority, is_blocked, parent_id) |
| `/work-items` | POST | Create work item |
| `/work-items/{id}` | GET | Get single work item |
| `/work-items/{id}` | PATCH | Update work item fields |
| `/work-items/{id}/transition` | POST | State transition with validation |
| `/work-items/{id}/block` | POST | Block with reason |
| `/work-items/{id}/unblock` | POST | Unblock |
| `/work-items/{id}/children` | GET | List children with progress |
| `/work-items/{id}/assignments` | GET/POST | List/create assignments |
| `/work-items/{id}/assignments/current` | GET | Current assignment |
| `/work-items/{id}/runs` | GET/POST | List/create execution records |
| `/work-items/{id}/reviews` | GET/POST | List/create reviews |
| `/work-items/{id}/attachments` | GET/POST | List/create attachments |
| `/executors/{name}/work-items` | GET | Work items by executor |
| `/repositories` | GET/POST | List/create repositories |
| `/repositories/{name}` | GET/PATCH/DELETE | Repository CRUD |
| `/activity` | GET | Activity log (filter: task_id, limit) |
| `/status` | GET | Status overview (counts, executing, blocked, awaiting_review) |
| `/issues` | GET | Legacy alias for `/work-items` |
| `/docs` | GET | Auto-generated OpenAPI docs |

---

## Dependencies

**Runtime:** Python 3.13+, FastAPI, SQLModel (SQLAlchemy + Pydantic), Rich, Typer, uvicorn
**Test:** pytest, datetime-truncate
**Package manager:** uv

---

## Data Model

Five core objects, all defined as SQLModel tables in `models.py`. The data model diagram below reflects the implemented schema:

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│  Repository  │◄──FK──│    Work Item      │──FK──►│  Assignment  │
│              │       │  (unified)        │       │              │
│  repo_id     │       │  task_id          │       │  assignment_id│
│  name        │       │  repo_id (FK)     │       │  task_id (FK)│
│  org         │       │  title            │       │  executor    │
│  default_branch│     │  description      │       │  executor_type│
│  status      │       │  state            │       │  assigned_at │
│  url         │       │  priority         │       └──────────────┘
│  description │       │  is_blocked       │
└──────────────┘       │  blocked_reason   │       ┌──────────────────┐
                       │  parent_id (FK)   │──FK──►│ Execution Record │
                       │  created_by       │       │                  │
                       │  created_at       │       │  run_id          │
                       │  updated_at       │       │  task_id (FK)    │
                       └──────────────────┘       │  executor        │
                              │                    │  branch          │
                              │ FK                 │  commit          │
                              ▼                    │  status          │
                       ┌──────────────┐           │  logs_ref        │
                       │   Review     │           │  artifact_ref    │
                       │              │           │  created_at      │
                       │  review_id   │           └──────────────────┘
                       │  task_id (FK)│
                       │  reviewer    │
                       │  decision    │
                       │  note        │
                       │  created_at  │
                       └──────────────┘
```

All seven tables are actively used. The data model diagram above shows the five core objects; `activity_log` and `attachments` tables are documented in the schema section above.

### State Engine

ForgeOps owns the state machine. The lifecycle is agent-aware — not generic project management.

```
queued → assigned → executing → completed → awaiting_review → accepted → closed
                        ↑                                        │
                        └──────── rework_required ───────────────┘
```

**Key rules:**
- **Block mechanism** is orthogonal — `is_blocked` + `blocked_reason` on any state. Unblocking resumes where it was.
- **Repo concurrency guard** — one `executing` item per `repo_id` at a time. Prevents conflicting changes by parallel agents.
- **Parallel work** — no global locks. An executor can have multiple assignments across different repos in different states concurrently.
- **Event hooks** (Phase 3) — layered on top. Seven events (`on_state_change`, `on_blocked`/`on_unblocked`, `on_assigned`, `on_execution_complete`, `on_review_submitted`, `on_repo_conflict`, `on_rework`) fire after transitions commit.

---

## Mapping to Roadmap

### What exists today (after Phase 2)

| Target object | Current state | Where in code |
|---------------|---------------|---------------|
| Repository | Full metadata + CRUD. Active/archived filtering. | `models.Repository`, `core/database.py`, `core/repository_manager.py` |
| Work Item | Unified `work_items` table with state engine validation. | `models.WorkItem`, `core/database.py` |
| Assignment | Append-only history, `my-issues`, `agent-tasks`. | `models.Assignment`, `core/database.py`, `commands/assign.py` |
| Execution Record | Multiple attempts per item, git auto-detect. | `models.ExecutionRecord`, `core/database.py`, `commands/execution.py` |
| Review | Review queue, approve/request-changes workflow. | `models.Review`, `core/database.py`, `commands/review.py` |
| State Engine | 8-state lifecycle, transition validation, repo concurrency guard. | `core/state_engine.py`, `core/database.py` |
| Session Continuity | `status`, `next`, `snapshot`/`resume`, activity log. | `commands/session.py`, `models.ActivityLog` |
| Attachments | General-purpose links on work items. | `models.Attachment`, `commands/attachments.py` |
| Task Hierarchy | Parent-child relationships with progress rollup. | `commands/tasks.py`, `core/database.py` |

### Phase 1 (complete)

- Dual storage retired: SQLite via SQLModel is the single source of truth
- `FileManager`, `TaskManager`, `IssueTracker`, old `Database` retired
- Issues and tasks unified into `work_items` table
- All five core models defined with Pydantic validation
- Rich CLI output, repository autocompletion
- `config.py` with environment variable support

### Phase 2 (complete)

- State engine with transition validation and repo concurrency guard (`core/state_engine.py`)
- Assignments — append-only history, `executor_type` discriminator (human | agent)
- Execution records — branch, commit, status, logs_ref, artifact_ref; multiple attempts per work item
- Review workflow — review queue fed by execution records, append-only decision log
- Session continuity — `status`, `snapshot`/`resume`, `next`, activity log
- Attachments — general-purpose links on work items
- Task hierarchy — parent-child relationships with progress rollup
- 27 CLI commands, 110 tests passing

### Phase 3 (in progress)

Completed:
- Full CRUD REST API with 20+ endpoints replacing the old 2-endpoint `api.py`
- Bearer token auth (via `API_BEARER_TOKEN` env var)
- Event hook system (`core/hooks.py`) — 7 events firing from database operations
- 155 tests passing (45 new Phase 3 tests for API + hooks)

Remaining:
- JCT integration via hooks
- MCP server for AI agent access
