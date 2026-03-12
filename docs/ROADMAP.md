# ForgeOps Roadmap

ForgeOps is a **cross-repo work ledger**. It tracks six core capabilities:

| Capability | Current state |
|---|---|
| Repositories | Name registry only — no metadata |
| Issues / Tasks | Two disconnected systems — not linked, tasks not in CLI or API |
| Assignments | Not implemented |
| Progress states | Tasks have free-text `status`; issues have no status |
| Artifacts / References | Not implemented |
| Review outcomes | Not implemented |

The roadmap is structured to build these capabilities incrementally across three phases.

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

*Focus: Implement assignments, progress states, artifacts, and reviews — the four missing ledger pillars.*

### Assignments

- [ ] **Assigned-to field:** Add `assigned_to` to work items. CLI: `assign-issue <ID> <person>`, `my-issues`.
- [ ] **Ownership history:** Record assignment changes with timestamps (who, when, from/to).

### Progress States

- [ ] **State machine:** Define allowed states (`Open`, `In Progress`, `Blocked`, `Resolved`, `Closed`) and valid transitions.
- [ ] **Status commands:** `update-issue <ID> --status <state>` with transition validation.
- [ ] **Filter by state:** `list-issues --status open`, `list-issues --status blocked`.
- [ ] **Priority levels:** `Low`, `Medium`, `High`, `Urgent` — filterable and sortable.

### Artifacts & References

- [ ] **Attachments table:** Link work items to external references — URLs, file paths, commit SHAs, PR numbers.
- [ ] **CLI commands:** `attach <ISSUE-ID> <url-or-path>`, `list-attachments <ISSUE-ID>`.
- [ ] **Git integration:** Auto-detect current repository and branch when creating issues.

### Review Outcomes

- [ ] **Review model:** Reviewer assignment, decision (approve / request-changes / reject), comments, timestamp.
- [ ] **CLI commands:** `request-review <ISSUE-ID> <reviewer>`, `submit-review <ISSUE-ID> --decision approve`.
- [ ] **Decision log:** Append-only history of review decisions per work item.

### Task Hierarchy

- [ ] **Sub-tasks:** Work items can have a `parent_id` linking to another work item.
- [ ] **Progress rollup:** Auto-calculate parent completion percentage from child statuses.
- [ ] **CLI:** `add-task <PARENT-ID> <title>`, `list-tasks <ISSUE-ID>`.

---

## Phase 3: API & Ecosystem

*Focus: Expose the full ledger over HTTP and add operational tooling.*

### Web API

- [ ] **Full CRUD API:** POST, GET, PATCH, DELETE for work items, repositories, attachments, and reviews.
- [ ] **API authentication:** Bearer token or API key auth.
- [ ] **Filtering & search:** Query params for status, priority, assignee, repository. Full-text search on title/description.

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
- [ ] **Webhook notifications:** Fire events on state transitions for external integrations.
