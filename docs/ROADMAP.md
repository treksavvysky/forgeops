# ForgeOps Roadmap

ForgeOps is a **cross-repo work ledger for AI-assisted software development**. It exists to keep issues, tasks, progress, and next actions visible so that work remains organized, reviewable, and resumable across sessions and repositories.

The core problem: when AI agents (like Jules) generate code across multiple repos, the human operator needs to track what was done, what needs review, what's next, and where things stood when they last stepped away. ForgeOps separates AI execution from human review, allowing work to continue in parallel while preserving operational continuity.

### Core data objects

| Object | Current state |
|---|---|
| **Repository** — `repo_id`, `name`, `org`, `default_branch`, `status`, `url`, `description` | Name registry only — no metadata |
| **Work Item** (issue/task) — `task_id`, `repo_id` (FK), `title`, `description`, `state`, `priority`, `parent_id`, `created_by`, `created_at`, `updated_at` | Two disconnected systems — issues (JSON) and tasks (JSON), not linked |
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

- [ ] **Unified work-item schema:** Collapse issues and tasks into one `work_items` table with: task_id, repo_id (FK), title, description, state, priority, parent_id (for sub-tasks), created_by, created_at, updated_at.
- [ ] **Pydantic models:** Define `WorkItem`, `Repository`, `Assignment`, `ExecutionRecord`, and `Review` models for strict validation across CLI, API, and DB layers.
- [ ] **SQLModel integration:** Replace raw sqlite3 queries and JSON file storage with SQLModel for type-safe DB interactions. Retire the dual-storage (JSON files + SQLite) model.
- [ ] **Centralized configuration:** Move hardcoded paths (`forgeops.db`, `issues/`) to a `config.py` supported by environment variables.
- [ ] **Migration path:** Provide a one-time migration from the current JSON files + old schema into the new unified schema.

### Repositories

- [ ] **Repository metadata:** Extend the `repositories` table with org, default_branch, status (active/archived), url, and description fields.
- [ ] **Repository CRUD:** Add `update-repo` and `remove-repo` CLI commands.
- [ ] **Repository status:** Filter commands respect active/archived status. Archived repos excluded from default views.

### CLI & UX

- [x] **Modern CLI framework:** Migrated to Typer. *(done 2026-03-12, `218b783`)*
- [ ] **Rich CLI output:** Use `rich` (already installed as Typer dependency) for color-coded status indicators and formatted tables.
- [ ] **Repository autocompletion:** Typer callback that completes `--repo` values from the registry. *(basic shell completion available via `--install-completion`)*

---

## Phase 2: Work Ledger Capabilities

*Focus: Implement the four missing ledger pillars, plus session continuity and AI-aware review workflows.*

### Assignments

- [ ] **Assignments table:** Separate `assignments` table (not a field on work items). Each assignment is a first-class record: `assignment_id`, `task_id` (FK), `executor`, `executor_type` (human | agent), `assigned_at`.
- [ ] **Assignment CLI:** `assign <ID> <executor> --type human|agent`, `my-issues`, `agent-tasks <executor>`.
- [ ] **Assignment history:** The assignments table is append-only — reassignment creates a new record, preserving full ownership history.

### Progress States

- [ ] **State machine:** Define allowed states (`Open`, `In Progress`, `Blocked`, `Review`, `Resolved`, `Closed`) and valid transitions.
- [ ] **Status commands:** `update-issue <ID> --status <state>` with transition validation.
- [ ] **Filter by state:** `list-issues --status open`, `list-issues --status blocked`, `list-issues --status review`.
- [ ] **Priority levels:** `Low`, `Medium`, `High`, `Urgent` — filterable and sortable.

### Session Continuity

- [ ] **Work snapshots:** Capture current state across all open work items — what's in progress, what's blocked, what's awaiting review. CLI: `snapshot`, `resume` (shows snapshot from last session).
- [ ] **Activity log:** Append-only record of state changes, comments, and assignments — so the operator can see what happened while they were away.
- [ ] **Next-actions view:** `next` command that surfaces the highest-priority items needing human attention (items in `Review` state, blocked items, stale assignments).

### Execution Records

- [ ] **Execution records table:** Separate `execution_records` table tracking what an agent or human actually did: `run_id`, `task_id` (FK), `executor`, `branch`, `commit`, `status` (success | failed | partial), `logs_ref`, `artifact_ref`, `created_at`.
- [ ] **Execution CLI:** `log-run <TASK-ID> --branch <branch> --commit <sha> --status success`, `runs <TASK-ID>` (list all execution attempts).
- [ ] **Review context:** The review queue draws from execution records — reviewer sees branch, commit, status, and linked artifacts for each run.
- [ ] **Multiple attempts:** A single work item can have multiple execution records (failed attempts, retries, iterative changes).

### AI-Generated Code Review

- [ ] **Review queue:** Work items in `Review` state represent AI-generated output awaiting human inspection. `review-queue` lists them with execution record context (branch, commit, what changed).
- [ ] **Review workflow:** `start-review <ID>`, `approve <ID>`, `request-changes <ID> --note "..."`. Each review is a record: `review_id`, `task_id` (FK), `reviewer`, `decision`, `note`, `created_at`.
- [ ] **Decision log:** The reviews table is append-only — full history of review decisions per work item.

### Artifacts & References

- [ ] **Structured references:** Execution records carry `logs_ref` and `artifact_ref` pointers for run-specific outputs. Separate `attachments` table for general-purpose links (URLs, file paths, PR numbers) not tied to a specific run.
- [ ] **CLI commands:** `attach <TASK-ID> <url-or-path>`, `list-attachments <TASK-ID>`.
- [ ] **Git integration:** Auto-detect current repository and branch when creating issues or logging runs.

### Task Hierarchy

- [ ] **Sub-tasks:** Work items can have a `parent_id` linking to another work item.
- [ ] **Progress rollup:** Auto-calculate parent completion percentage from child statuses.
- [ ] **CLI:** `add-task <PARENT-ID> <title>`, `list-tasks <ISSUE-ID>`.

---

## Phase 3: API & Ecosystem Integration

*Focus: Expose the full ledger over HTTP and connect ForgeOps to the broader AI development system.*

### Web API

- [ ] **Full CRUD API:** POST, GET, PATCH, DELETE for work items, repositories, assignments, execution records, reviews, and attachments.
- [ ] **API authentication:** Bearer token or API key auth.
- [ ] **Filtering & search:** Query params for status, priority, assignee, repository. Full-text search on title/description.

### Ecosystem Hooks

- [ ] **JCT integration:** When JCT dispatches a task to an AI agent, ForgeOps creates an assignment and work item. When the agent completes, an execution record is logged and the item moves to `Review`.
- [ ] **Event bus:** Fire events on state transitions (e.g., item moved to `Review`) that other systems can subscribe to.
- [ ] **MCP server:** Expose ForgeOps as an MCP tool server so AI agents can read/update the ledger directly.

### Quality & DevOps

- [ ] **Expanded test suite:**
    - [x] Integration tests for CLI commands. *(done 2026-03-12, `0ced06b`)*
    - [ ] Tests for new ledger capabilities (assignments, states, artifacts, reviews).
    - [ ] Property-based testing for data validation.
- [ ] **GitHub Actions CI:** Automate linting (`ruff`), type-checking (`mypy`), and testing on every push.
- [ ] **Dockerization:** Dockerfile for the API and CLI.

### Future Ideas

- [ ] **Markdown / PDF exports:** Issue summaries and project status reports.
- [ ] **Multi-user support:** User accounts, permissions, team-scoped views.
- [ ] **Automated scoring:** Track AI agent reliability — approval rates, revision frequency, time-to-review.
