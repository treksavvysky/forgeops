# ForgeOps Roadmap

ForgeOps is a **cross-repo work ledger for AI-assisted software development**. It exists to keep issues, tasks, progress, and next actions visible so that work remains organized, reviewable, and resumable across sessions and repositories.

The core problem: when AI agents (like Jules) generate code across multiple repos, the human operator needs to track what was done, what needs review, what's next, and where things stood when they last stepped away. ForgeOps separates AI execution from human review, allowing work to continue in parallel while preserving operational continuity.

### Six capabilities

| Capability | Current state |
|---|---|
| Repositories | Name registry only — no metadata |
| Issues / Tasks | Two disconnected systems — not linked, tasks not in CLI or API |
| Assignments | Not implemented |
| Progress states | Tasks have free-text `status`; issues have no status |
| Artifacts / References | Not implemented |
| Review outcomes | Not implemented |

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

- [ ] **Unified work-item schema:** Collapse issues and tasks into one `work_items` table with: id, title, description, repository (FK), status, priority, assigned_to, parent_id (for sub-tasks), created_by, created_at, updated_at.
- [ ] **Pydantic models:** Define `WorkItem`, `Repository`, and related models for strict validation across CLI, API, and DB layers.
- [ ] **SQLModel integration:** Replace raw sqlite3 queries and JSON file storage with SQLModel for type-safe DB interactions. Retire the dual-storage (JSON files + SQLite) model.
- [ ] **Centralized configuration:** Move hardcoded paths (`forgeops.db`, `issues/`) to a `config.py` supported by environment variables.
- [ ] **Migration path:** Provide a one-time migration from the current JSON files + old schema into the new unified schema.

### Repositories

- [ ] **Repository metadata:** Extend the `repositories` table with url, description, and owner fields.
- [ ] **Repository CRUD:** Add `update-repo` and `remove-repo` CLI commands.

### CLI & UX

- [x] **Modern CLI framework:** Migrated to Typer. *(done 2026-03-12, `218b783`)*
- [ ] **Rich CLI output:** Use `rich` (already installed as Typer dependency) for color-coded status indicators and formatted tables.
- [ ] **Repository autocompletion:** Typer callback that completes `--repo` values from the registry. *(basic shell completion available via `--install-completion`)*

---

## Phase 2: Work Ledger Capabilities

*Focus: Implement the four missing ledger pillars, plus session continuity and AI-aware review workflows.*

### Assignments

- [ ] **Assigned-to field:** Add `assigned_to` to work items. Support both human operators and AI agents as assignees. CLI: `assign-issue <ID> <person>`, `my-issues`.
- [ ] **Ownership history:** Record assignment changes with timestamps (who, when, from/to).

### Progress States

- [ ] **State machine:** Define allowed states (`Open`, `In Progress`, `Blocked`, `Review`, `Resolved`, `Closed`) and valid transitions.
- [ ] **Status commands:** `update-issue <ID> --status <state>` with transition validation.
- [ ] **Filter by state:** `list-issues --status open`, `list-issues --status blocked`, `list-issues --status review`.
- [ ] **Priority levels:** `Low`, `Medium`, `High`, `Urgent` — filterable and sortable.

### Session Continuity

- [ ] **Work snapshots:** Capture current state across all open work items — what's in progress, what's blocked, what's awaiting review. CLI: `snapshot`, `resume` (shows snapshot from last session).
- [ ] **Activity log:** Append-only record of state changes, comments, and assignments — so the operator can see what happened while they were away.
- [ ] **Next-actions view:** `next` command that surfaces the highest-priority items needing human attention (items in `Review` state, blocked items, stale assignments).

### AI-Generated Code Review

- [ ] **Review queue:** Work items in `Review` state represent AI-generated output awaiting human inspection. `review-queue` lists them with context (repo, branch, what changed).
- [ ] **Review workflow:** `start-review <ID>`, `approve <ID>`, `request-changes <ID> --note "..."`. Captures decision, reviewer, timestamp.
- [ ] **Decision log:** Append-only history of review decisions per work item.

### Artifacts & References

- [ ] **Attachments table:** Link work items to external references — URLs, file paths, commit SHAs, PR numbers, branch names.
- [ ] **CLI commands:** `attach <ISSUE-ID> <url-or-path>`, `list-attachments <ISSUE-ID>`.
- [ ] **Git integration:** Auto-detect current repository and branch when creating issues.

### Task Hierarchy

- [ ] **Sub-tasks:** Work items can have a `parent_id` linking to another work item.
- [ ] **Progress rollup:** Auto-calculate parent completion percentage from child statuses.
- [ ] **CLI:** `add-task <PARENT-ID> <title>`, `list-tasks <ISSUE-ID>`.

---

## Phase 3: API & Ecosystem Integration

*Focus: Expose the full ledger over HTTP and connect ForgeOps to the broader AI development system.*

### Web API

- [ ] **Full CRUD API:** POST, GET, PATCH, DELETE for work items, repositories, attachments, and reviews.
- [ ] **API authentication:** Bearer token or API key auth.
- [ ] **Filtering & search:** Query params for status, priority, assignee, repository. Full-text search on title/description.

### Ecosystem Hooks

- [ ] **JCT integration:** When JCT dispatches a task to an AI agent, ForgeOps creates or updates the corresponding work item. When the agent completes, the item moves to `Review`.
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
