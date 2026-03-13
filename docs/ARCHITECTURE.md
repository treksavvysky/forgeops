# ForgeOps Architecture

This document describes the current architecture of ForgeOps and how it maps to the roadmap's target state.

---

## System Purpose

ForgeOps is the work-tracking ledger for AI-assisted development. It records what work exists, what state it's in, who or what is responsible, and what outcomes were produced — so that development remains organized and resumable across sessions, repositories, and agents.

See [PURPOSE.md](PURPOSE.md) for full scope boundaries. See [ROADMAP.md](ROADMAP.md) for the build plan.

---

## Current Architecture

*Updated after Phase 1 completion (2026-03-13).*

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
│  │  create_issue │              │                      │
│  │  list_issues  │              │                      │
│  │  view_issue   │              │                      │
│  │  list_repos   │              │                      │
│  │  add_repo     │              │                      │
│  │  update_repo  │              │                      │
│  │  remove_repo  │              │                      │
│  │  migrate_issues│             │                      │
│  └──────┬───────┘              │                      │
├─────────┼──────────────────────┼─────────────────────┤
│  Core                          │                      │
│  ┌─────────────────────────────┴───────────────────┐ │
│  │  database.py        — SQLModel data access layer │ │
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
        │  │  assignments (Phase 2)     │ │
        │  │  execution_records (Ph. 2) │ │
        │  │  reviews (Phase 2)         │ │
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

**`assignments` table** (schema defined, populated in Phase 2)
| Column | Type | Constraints |
|--------|------|-------------|
| assignment_id | INTEGER | PRIMARY KEY |
| task_id | INTEGER | FK → work_items.task_id |
| executor | TEXT | NOT NULL |
| executor_type | TEXT | "human" / "agent" |
| assigned_at | DATETIME | auto-set |

**`execution_records` table** (schema defined, populated in Phase 2)
| Column | Type | Constraints |
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

**`reviews` table** (schema defined, populated in Phase 2)
| Column | Type | Constraints |
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
  ├── commands/create_issue  → core/database, core/repository_manager, utils/validators
  ├── commands/list_issues   → core/database, models
  ├── commands/view_issue    → core/database
  ├── commands/list_repos    → core/database
  ├── commands/add_repo      → core/database, core/repository_manager
  ├── commands/update_repo   → core/database, core/repository_manager
  ├── commands/remove_repo   → core/database, core/repository_manager
  └── commands/migrate_issues → core/database, config

api.py → core/database, models
```

---

## Interfaces

### CLI (`main.py`)

Typer-based with 8 commands. Rich output for tables and panels. Interactive input via `InputValidator`. Repository autocompletion on `--repo`.

| Command | Args/Options | Storage |
|---------|-------------|---------|
| `create-issue` | `--priority`, `--created-by` (interactive) | writes `forgeops.db` |
| `list-issues` | `--repo`, `--state`, `--blocked` | reads `forgeops.db` |
| `view-issue` | `WI-<n>` or `<n>` | reads `forgeops.db` |
| `list-repos` | `--all` (includes archived) | reads `forgeops.db` |
| `add-repo` | `<name>`, `--org`, `--branch`, `--url`, `--description` | writes `forgeops.db` |
| `update-repo` | `<name>`, `--org`, `--branch`, `--status`, `--url`, `--description` | writes `forgeops.db` |
| `remove-repo` | `<name>` | writes `forgeops.db` |
| `migrate-issues` | — | reads legacy JSON, writes `forgeops.db` |

### REST API (`api.py`)

Two endpoints. No authentication. Reads/writes through `core/database.py`.

| Endpoint | Method | Response |
|----------|--------|----------|
| `/issues` | GET | Work items (filterable by `repo`, `state`) |
| `/repositories` | GET | Repository list (filterable by `include_archived`) |
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

All five tables exist in the database. Repository and WorkItem are actively used. Assignment, ExecutionRecord, and Review tables are created but will be populated by Phase 2 commands.

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

### What exists today (after Phase 1)

| Target object | Current state | Where in code |
|---------------|---------------|---------------|
| Repository | Full metadata (name, org, branch, status, url, description). CRUD via CLI + API. Active/archived filtering. | `models.Repository`, `core/database.py`, `core/repository_manager.py` |
| Work Item | Unified `work_items` table. State and priority fields present but no transition validation yet. | `models.WorkItem`, `core/database.py` |
| Assignment | Table exists in DB schema, model defined. No CLI/API commands yet. | `models.Assignment` |
| Execution Record | Table exists in DB schema, model defined. No CLI/API commands yet. | `models.ExecutionRecord` |
| Review | Table exists in DB schema, model defined. No CLI/API commands yet. | `models.Review` |
| State Engine | States defined as enum. No transition validation, no concurrency guard. | `models.WorkItemState` |
| Session Continuity | Not implemented. No `status`, `snapshot`, `resume`, or `next` commands. | — |

### Phase 1 (complete)

- Dual storage retired: SQLite via SQLModel is the single source of truth
- `FileManager`, `TaskManager`, `IssueTracker`, old `Database` retired
- Issues and tasks unified into `work_items` table
- All five core models defined with Pydantic validation
- Rich CLI output, repository autocompletion
- `config.py` with environment variable support

### Phase 2 additions to this architecture

New core modules for:
- **State engine** — 8-state lifecycle with transition validation, orthogonal block mechanism, repo concurrency guard
- **Assignments** — separate table, append-only history, `executor_type` discriminator (human | agent)
- **Execution records** — structured record of agent runs (branch, commit, status, logs_ref, artifact_ref), multiple attempts per work item
- **Review workflow** — review queue fed by execution records, append-only decision log
- **Session continuity** — `status` (overview), `snapshot`/`resume` (cross-session state), `next` (human attention queue), activity log
- **Artifacts** — run-specific refs on execution records + general-purpose attachments table
- **Task hierarchy** — parent-child relationships, progress rollup

### Phase 3 additions to this architecture

- Full CRUD REST API replacing the current single-endpoint `api.py`
- Authentication layer (bearer token / API key)
- **Event hooks** — 7 subscribable events layered on the state engine, driving JCT integration and external notifications
- **MCP server** — AI agents read/update the ledger directly
- The three-layer design remains, but the interface layer expands significantly
