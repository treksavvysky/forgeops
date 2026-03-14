# ForgeOps Roadmap

ForgeOps is a **cross-repo work ledger for AI-assisted software development**. It exists to keep issues, tasks, progress, and next actions visible so that work remains organized, reviewable, and resumable across sessions and repositories.

The core problem: when AI agents (like Jules) generate code across multiple repos, the human operator needs to track what was done, what needs review, what's next, and where things stood when they last stepped away. ForgeOps separates AI execution from human review, allowing work to continue in parallel while preserving operational continuity.

### Core data objects

| Object | Current state |
|---|---|
| **Repository** — `repo_id`, `name`, `org`, `default_branch`, `status`, `url`, `description` | Name registry only — no metadata |
| **Work Item** (issue/task) — `task_id`, `repo_id` (FK), `title`, `description`, `state`, `priority`, `is_blocked`, `blocked_reason`, `parent_id`, `created_by`, `created_at`, `updated_at` | Two disconnected systems — issues (JSON) and tasks (JSON), not linked |
| **Assignment** — `assignment_id`, `task_id` (FK), `executor`, `executor_type` (human\|agent), `assigned_at` | Not implemented |
| **Execution Record** — `run_id`, `task_id` (FK), `executor`, `branch`, `commit`, `status`, `logs_ref`, `artifact_ref`, `created_at` | Not implemented |
| **Review** — `review_id`, `task_id` (FK), `reviewer`, `decision`, `note`, `created_at` | Not implemented |

### Ecosystem context

ForgeOps is the work-tracking layer in a larger AI development system:

- **JCT** — Task dispatch and execution control for AI agents
- **Action Registry** — Atomic agent moves (the "verbs" agents can perform)
- **Aegis** — Secrets and credential management
- **Charon** — SSH connection management for AI agents

ForgeOps does not duplicate these systems. It is the ledger that records *what work happened*, *what state it's in*, and *what needs human attention*.

---

## Phase 1: Unified Foundation

*Focus: Merge issues and tasks into a single data model backed by SQLite, with proper schema and validation.*

### Data Model

- [x] **Unified work-item schema:** Collapse issues and tasks into one `work_items` table with: task_id, repo_id (FK), title, description, state, priority, is_blocked, blocked_reason, parent_id (for sub-tasks), created_by, created_at, updated_at. *(done 2026-03-13)*
- [x] **Pydantic models:** Define `WorkItem`, `Repository`, `Assignment`, `ExecutionRecord`, and `Review` models for strict validation across CLI, API, and DB layers. *(done 2026-03-13)*
- [x] **SQLModel integration:** Replace raw sqlite3 queries and JSON file storage with SQLModel for type-safe DB interactions. Retire the dual-storage (JSON files + SQLite) model. *(done 2026-03-13)*
- [x] **Centralized configuration:** Move hardcoded paths (`forgeops.db`, `issues/`) to a `config.py` supported by environment variables. *(done 2026-03-13)*
- [x] **Migration path:** Provide a one-time migration from the current JSON files + old schema into the new unified schema. *(done 2026-03-13)*

### Repositories

- [x] **Repository metadata:** Extend the `repositories` table with org, default_branch, status (active/archived), url, and description fields. *(done 2026-03-13)*
- [x] **Repository CRUD:** Add `update-repo` and `remove-repo` CLI commands. *(done 2026-03-13)*
- [x] **Repository status:** Filter commands respect active/archived status. Archived repos excluded from default views. *(done 2026-03-13)*

### CLI & UX

- [x] **Modern CLI framework:** Migrated to Typer. *(done 2026-03-12, `218b783`)*
- [x] **Rich CLI output:** Use `rich` (already installed as Typer dependency) for color-coded status indicators and formatted tables. *(done 2026-03-13)*
- [x] **Repository autocompletion:** Typer callback that completes `--repo` values from the registry. *(done 2026-03-13)*

---

## Phase 2: Work Ledger Capabilities

*Focus: Implement the four missing ledger pillars, plus session continuity and AI-aware review workflows.*

### Assignments

- [x] **Assignments table:** Separate `assignments` table (not a field on work items). Each assignment is a first-class record: `assignment_id`, `task_id` (FK), `executor`, `executor_type` (human | agent), `assigned_at`. *(done 2026-03-13)*
- [x] **Assignment CLI:** `assign <ID> <executor> --type human|agent`, `my-issues`, `agent-tasks <executor>`. *(done 2026-03-13)*
- [x] **Assignment history:** The assignments table is append-only — reassignment creates a new record, preserving full ownership history. *(done 2026-03-13)*

### State Engine

ForgeOps owns the state machine. The lifecycle reflects the AI-assisted workflow — not generic project management.

- [x] **Lifecycle states:** Eight states with transition validation via `core/state_engine.py`. *(done 2026-03-13)*

  ```
  queued → assigned → executing → completed → awaiting_review → accepted → closed
                          ↑                                        │
                          └──────── rework_required ───────────────┘
  ```

- [x] **Block mechanism:** Orthogonal `is_blocked` + `blocked_reason` on any state. `block()` / `unblock()` in `core/database.py`. *(done 2026-03-13)*
- [x] **Block CLI:** `block <ID> --reason "..."`, `unblock <ID>`. Blocked items surfaced in `next` and filtered views. *(done 2026-03-13)*
- [x] **Repo concurrency guard:** `check_repo_concurrency()` in state engine rejects `executing` if another item for same repo is already executing. *(done 2026-03-13)*
- [x] **Parallel work:** Per-work-item transitions, no global locks. Multiple assignments across repos concurrently. *(done 2026-03-13)*
- [x] **Status commands:** `update-status <ID> --state <state>` with transition validation. Invalid transitions rejected with clear error. *(done 2026-03-13)*
- [x] **Filter by state:** `list-issues --state queued`, `list-issues --state awaiting_review`, `list-issues --blocked`. *(done 2026-03-13)*
- [x] **Priority levels:** `Low`, `Medium`, `High`, `Urgent` — filterable via `--priority`. *(done 2026-03-13)*

### Session Continuity

- [x] **Work snapshots:** `snapshot` saves JSON, `resume` shows last session state. *(done 2026-03-13)*
- [x] **Activity log:** Append-only `activity_log` table records all state changes, assignments, blocks, reviews, executions. *(done 2026-03-13)*
- [x] **Status overview:** `status` command — items grouped by state, blocked items, executing repos, recent activity. *(done 2026-03-13)*
- [x] **Next-actions view:** `next` command surfaces `awaiting_review`, blocked, and `rework_required` items sorted by priority. *(done 2026-03-13)*

### Execution Records

- [x] **Execution records table:** `execution_records` table with full CRUD in `core/database.py`. *(done 2026-03-13)*
- [x] **Execution CLI:** `log-run` (with git auto-detect for branch/commit) and `runs <TASK-ID>`. *(done 2026-03-13)*
- [x] **Review context:** `review-queue` shows last execution record (branch, commit, status) per item. *(done 2026-03-13)*
- [x] **Multiple attempts:** Append-only — a work item can have multiple execution records. *(done 2026-03-13)*

### AI-Generated Code Review

- [x] **Review queue:** `review-queue` lists `awaiting_review` items with last execution record context. *(done 2026-03-13)*
- [x] **Review workflow:** `approve <ID>` and `request-changes <ID> --note "..."` with state transitions. *(done 2026-03-13)*
- [x] **Decision log:** `reviews` table is append-only — full history of review decisions per work item. *(done 2026-03-13)*

### Artifacts & References

- [x] **Structured references:** `logs_ref` and `artifact_ref` on execution records + `attachments` table for general-purpose links. *(done 2026-03-13)*
- [x] **CLI commands:** `attach <TASK-ID> <url-or-path>`, `list-attachments <TASK-ID>`. *(done 2026-03-13)*
- [x] **Git integration:** `log-run` auto-detects current branch and commit when not specified. *(done 2026-03-13)*

### Task Hierarchy

- [x] **Sub-tasks:** `parent_id` FK on work items enables task hierarchy. *(done 2026-03-13)*
- [x] **Progress rollup:** `get_child_progress()` calculates parent completion from child states. *(done 2026-03-13)*
- [x] **CLI:** `add-task <PARENT-ID> <title>`, `list-tasks <ISSUE-ID>` with progress bar. *(done 2026-03-13)*

---

## Phase 3: API & Ecosystem Integration

*Focus: Expose the full ledger over HTTP and connect ForgeOps to the broader AI development system.*

### Web API

- [x] **Full CRUD API:** POST, GET, PATCH, DELETE for work items, repositories, assignments, execution records, reviews, and attachments. Plus `/status`, `/activity`, `/executors/{name}/work-items` endpoints. *(done 2026-03-13)*
- [x] **API authentication:** Bearer token auth via `API_BEARER_TOKEN` env var. Skipped when unset. *(done 2026-03-13)*
- [x] **Filtering & search:** Query params for state, priority, is_blocked, repo, parent_id on `/work-items`. *(done 2026-03-13)*

### Event Hooks

Layered on top of the Phase 2 state engine. The engine already records state changes in the activity log — hooks make them actionable by external systems.

- [x] **Hook system:** `core/hooks.py` — `HookRegistry` with subscribe/unsubscribe/fire. Decorator and programmatic registration. Failing handlers logged, not raised. *(done 2026-03-13)*
- [x] **State engine events:** All 7 events implemented and firing from `core/database.py`: `on_state_change`, `on_blocked`/`on_unblocked`, `on_assigned`, `on_execution_complete`, `on_review_submitted`, `on_repo_conflict`, `on_rework`. *(done 2026-03-13)*
- [ ] **JCT integration:** When JCT dispatches a task, ForgeOps creates an assignment and work item. When the agent completes, an execution record is logged and the item moves to `awaiting_review`. Driven by `on_state_change` and `on_assigned` hooks.
- [x] **MCP server:** `mcp_server.py` — 19 tools exposing full ledger CRUD over stdio transport. Run via `uv run python mcp_server.py`. *(done 2026-03-13)*

### Quality & DevOps

- [ ] **Expanded test suite:**
    - [x] Integration tests for CLI commands. *(done 2026-03-12, `0ced06b`)*
    - [x] Tests for new ledger capabilities (assignments, states, artifacts, reviews). *(done 2026-03-13)*
    - [x] Property-based testing for data validation. *(done 2026-03-14, `tests/test_property.py`)*
- [x] **GitHub Actions CI:** Automate linting (`ruff`), type-checking (`mypy`), and testing on every push. *(done 2026-03-14, `.github/workflows/ci.yml`)*
- [x] **Dockerization:** Dockerfile for the API and CLI. *(done 2026-03-14, `9225229`)*

### Future Ideas

- [ ] **Markdown / PDF exports:** Issue summaries and project status reports.
- [ ] **Multi-user support:** User accounts, permissions, team-scoped views.
- [ ] **Automated scoring:** Track AI agent reliability — approval rates, revision frequency, time-to-review.
