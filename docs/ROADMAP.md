# Forge Ops Roadmap

This document outlines the planned improvements and future direction for the Forge Ops Issue Tracking System. The goals are divided into three phases: core stability, feature expansion, and ecosystem growth.

---

## Phase 1: Core Stability & Modernization
*Focus: Refactoring the foundation for better reliability and developer experience.*

### 🏗️ Architectural Enhancements
- [ ] **Automatic DB Synchronization:** Implement a "write-through" cache so that any CLI issue creation/modification automatically updates `forgeops.db`.
- [ ] **Pydantic Data Models:** Replace manual dictionary parsing with Pydantic models to ensure strict schema validation for JSON files and API responses.
- [ ] **SQLModel Integration:** Transition from raw SQLite queries to SQLModel (Pydantic + SQLAlchemy) for cleaner, type-safe database interactions.
- [ ] **Centralized Configuration:** Move hardcoded paths (e.g., `forgeops.db`, `issues/`) to a `config.py` file supported by environment variables.

### 💻 CLI & UX Improvements
- [ ] **Rich CLI Output:** Integrate the `rich` library to provide color-coded status indicators, formatted tables for `list-issues`, and Markdown rendering for descriptions.
- [x] **Modern CLI Framework:** Migrated to Typer with auto-generated `--help` and argument validation. *(done 2026-03-12, `218b783`)*
- [ ] **Repository Autocompletion:** Add shell completion support for repository names when using CLI commands. *(basic shell completion available via Typer's `--install-completion`; repo-specific value completion still needed)*

---

## Phase 2: Functional Expansion
*Focus: Turning the tool into a complete issue management lifecycle manager.*

### 🛠️ Issue Lifecycle Management
- [ ] **Update & Delete Commands:** Implement `update-issue` and `delete-issue` CLI commands.
- [ ] **Status Tracking:** Add support for issue states: `Open`, `In Progress`, `Blocked`, `Resolved`, and `Closed`.
- [ ] **Priority Levels:** Allow users to assign priorities (`Low`, `Medium`, `High`, `Urgent`) to issues.
- [ ] **Full-Text Search:** Implement a `search-issues` command to query titles and descriptions across the database.

### 📝 Task Integration
- [ ] **Interactive Task CLI:** Fully integrate `task_manager.py` into the CLI with commands like `add-task`, `list-tasks`, and `complete-task` linked to specific issues.
- [ ] **Sub-task Progress:** Automatically calculate and display issue completion percentages based on associated task statuses.

---

## Phase 3: API & Ecosystem
*Focus: Extending Forge Ops beyond a local CLI tool.*

### 🌐 Web API Maturity
- [ ] **Full CRUD API:** Expand the FastAPI service with POST, PATCH, and DELETE endpoints.
- [ ] **API Authentication:** Implement basic API key or OAuth2 authentication for the web service.
- [ ] **Swagger Documentation:** Auto-generate and polish interactive API docs at `/docs`.

### 🧪 Quality & DevOps
- [ ] **Expanded Test Suite:**
    - [x] Add integration tests for all CLI commands. *(done 2026-03-12, `0ced06b`)*
    - [ ] Implement property-based testing for data validation.
- [ ] **GitHub Actions CI:** Automate linting (`ruff`), type-checking (`mypy`), and testing on every push.
- [ ] **Dockerization:** Provide a `Dockerfile` to easily run the API and CLI in a containerized environment.

---

## Future Ideas
- [ ] **Git Integration:** Automatically detect the current repository and branch when creating issues.
- [ ] **Markdown Exports:** Export issue summaries or project status reports to Markdown/PDF.
- [ ] **Multi-user Support:** Explore multi-user database schemas for collaborative teams.
