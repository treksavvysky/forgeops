"""ForgeOps MCP Server — exposes the work ledger to AI agents.

Run: uv run python mcp_server.py
Or via entry point: forgeops-mcp
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    name="forgeops",
    instructions=(
        "ForgeOps: Cross-repo work ledger for AI-assisted development. "
        "Track work items through an 8-state lifecycle, manage assignments, "
        "log execution records, submit reviews, and monitor project status. "
        "All operations go through a single SQLite database."
    ),
)

# --- Lazy initialization ---------------------------------------------------

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from core.database import create_db_and_tables

        _engine = create_db_and_tables()
    return _engine


def _success(**kwargs) -> str:
    return json.dumps({"success": True, **kwargs}, default=str)


def _error(code: str, message: str) -> str:
    return json.dumps({"success": False, "error": {"code": code, "message": message}})


# --- Work Items -----------------------------------------------------------


@server.tool(
    name="forgeops_list_work_items",
    description="List work items with optional filters for repo, state, priority, blocked status, or parent.",
)
def forgeops_list_work_items(
    repo: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None,
    is_blocked: Optional[bool] = None,
    parent_id: Optional[int] = None,
) -> str:
    """List work items, optionally filtered."""
    try:
        from core.database import list_work_items
        from models import Priority, WorkItemState

        kwargs = {}
        if repo:
            kwargs["repo_name"] = repo
        if state:
            kwargs["state"] = WorkItemState(state)
        if priority:
            kwargs["priority"] = Priority(priority)
        if is_blocked is not None:
            kwargs["is_blocked"] = is_blocked
        if parent_id is not None:
            kwargs["parent_id"] = parent_id

        items = list_work_items(_get_engine(), **kwargs)
        return _success(items=[_serialize_item(i) for i in items], count=len(items))
    except ValueError as e:
        return _error("VALIDATION_ERROR", str(e))
    except Exception as e:
        return _error("LIST_ERROR", str(e))


@server.tool(
    name="forgeops_get_work_item",
    description="Get detailed information about a single work item by its task_id.",
)
def forgeops_get_work_item(task_id: int) -> str:
    """Get a work item by ID."""
    try:
        from core.database import get_work_item

        item = get_work_item(_get_engine(), task_id)
        if not item:
            return _error("NOT_FOUND", f"Work item {task_id} not found")
        return _success(item=_serialize_item(item))
    except Exception as e:
        return _error("GET_ERROR", str(e))


@server.tool(
    name="forgeops_create_work_item",
    description="Create a new work item. Optionally link to a repository and/or parent item.",
)
def forgeops_create_work_item(
    title: str,
    repo_name: Optional[str] = None,
    description: Optional[str] = None,
    priority: str = "medium",
    parent_id: Optional[int] = None,
    created_by: Optional[str] = None,
) -> str:
    """Create a work item."""
    try:
        from core.database import create_work_item, get_work_item
        from models import Priority

        item = create_work_item(
            _get_engine(),
            title,
            repo_name=repo_name,
            description=description,
            priority=Priority(priority),
            parent_id=parent_id,
            created_by=created_by,
        )
        refreshed = get_work_item(_get_engine(), item.task_id)
        return _success(item=_serialize_item(refreshed))
    except ValueError as e:
        return _error("VALIDATION_ERROR", str(e))
    except Exception as e:
        return _error("CREATE_ERROR", str(e))


@server.tool(
    name="forgeops_update_work_item",
    description="Update a work item's title, description, or priority.",
)
def forgeops_update_work_item(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """Update work item fields."""
    try:
        from core.database import update_work_item, get_work_item
        from models import Priority

        kwargs = {}
        if title is not None:
            kwargs["title"] = title
        if description is not None:
            kwargs["description"] = description
        if priority is not None:
            kwargs["priority"] = Priority(priority)

        if not kwargs:
            return _error("VALIDATION_ERROR", "No fields to update")

        item = update_work_item(_get_engine(), task_id, **kwargs)
        if not item:
            return _error("NOT_FOUND", f"Work item {task_id} not found")
        refreshed = get_work_item(_get_engine(), item.task_id)
        return _success(item=_serialize_item(refreshed))
    except ValueError as e:
        return _error("VALIDATION_ERROR", str(e))
    except Exception as e:
        return _error("UPDATE_ERROR", str(e))


# --- State Engine ---------------------------------------------------------


@server.tool(
    name="forgeops_transition",
    description=(
        "Transition a work item to a new state. Valid states: queued, assigned, executing, "
        "completed, awaiting_review, accepted, rework_required, closed. "
        "Validates transitions and enforces repo concurrency (one executing item per repo)."
    ),
)
def forgeops_transition(
    task_id: int,
    state: str,
    actor: Optional[str] = None,
) -> str:
    """Transition a work item to a new state."""
    try:
        from core.database import transition_work_item, get_work_item
        from models import WorkItemState

        item = transition_work_item(
            _get_engine(),
            task_id,
            WorkItemState(state),
            actor=actor,
        )
        refreshed = get_work_item(_get_engine(), item.task_id)
        return _success(item=_serialize_item(refreshed))
    except ValueError as e:
        return _error("NOT_FOUND", str(e))
    except Exception as e:
        error_type = type(e).__name__
        return _error(error_type.upper(), str(e))


@server.tool(
    name="forgeops_block",
    description="Block a work item with a reason. Blocking is orthogonal to lifecycle state.",
)
def forgeops_block(
    task_id: int,
    reason: str,
    actor: Optional[str] = None,
) -> str:
    """Block a work item."""
    try:
        from core.database import block_work_item, get_work_item

        block_work_item(_get_engine(), task_id, reason, actor=actor)
        refreshed = get_work_item(_get_engine(), task_id)
        return _success(item=_serialize_item(refreshed))
    except ValueError as e:
        return _error("NOT_FOUND", str(e))
    except Exception as e:
        return _error("BLOCK_ERROR", str(e))


@server.tool(
    name="forgeops_unblock",
    description="Unblock a work item. Resumes at its current lifecycle state.",
)
def forgeops_unblock(
    task_id: int,
    actor: Optional[str] = None,
) -> str:
    """Unblock a work item."""
    try:
        from core.database import unblock_work_item, get_work_item

        unblock_work_item(_get_engine(), task_id, actor=actor)
        refreshed = get_work_item(_get_engine(), task_id)
        return _success(item=_serialize_item(refreshed))
    except ValueError as e:
        return _error("NOT_FOUND", str(e))
    except Exception as e:
        return _error("UNBLOCK_ERROR", str(e))


# --- Assignments ----------------------------------------------------------


@server.tool(
    name="forgeops_assign",
    description="Assign a work item to an executor (human or agent). Creates a new assignment record.",
)
def forgeops_assign(
    task_id: int,
    executor: str,
    executor_type: str = "human",
    actor: Optional[str] = None,
) -> str:
    """Assign a work item."""
    try:
        from core.database import create_assignment, get_work_item
        from models import ExecutorType

        item = get_work_item(_get_engine(), task_id)
        if not item:
            return _error("NOT_FOUND", f"Work item {task_id} not found")

        assignment = create_assignment(
            _get_engine(),
            task_id,
            executor,
            ExecutorType(executor_type),
            actor=actor,
        )
        return _success(
            assignment={
                "assignment_id": assignment.assignment_id,
                "task_id": assignment.task_id,
                "executor": assignment.executor,
                "executor_type": assignment.executor_type.value,
                "assigned_at": str(assignment.assigned_at),
            }
        )
    except ValueError as e:
        return _error("VALIDATION_ERROR", str(e))
    except Exception as e:
        return _error("ASSIGN_ERROR", str(e))


@server.tool(
    name="forgeops_my_items",
    description="List work items currently assigned to an executor (latest assignment wins).",
)
def forgeops_my_items(executor: str) -> str:
    """Get work items for an executor."""
    try:
        from core.database import list_items_by_executor

        items = list_items_by_executor(_get_engine(), executor)
        return _success(items=[_serialize_item(i) for i in items], count=len(items))
    except Exception as e:
        return _error("LIST_ERROR", str(e))


# --- Execution Records ----------------------------------------------------


@server.tool(
    name="forgeops_log_run",
    description="Log an execution record for a work item. Records what an agent or human actually did.",
)
def forgeops_log_run(
    task_id: int,
    executor: str,
    status: str,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
    logs_ref: Optional[str] = None,
    artifact_ref: Optional[str] = None,
    actor: Optional[str] = None,
) -> str:
    """Log an execution record."""
    try:
        from core.database import create_execution_record, get_work_item
        from models import ExecutionStatus

        item = get_work_item(_get_engine(), task_id)
        if not item:
            return _error("NOT_FOUND", f"Work item {task_id} not found")

        record = create_execution_record(
            _get_engine(),
            task_id,
            executor,
            ExecutionStatus(status),
            branch=branch,
            commit=commit,
            logs_ref=logs_ref,
            artifact_ref=artifact_ref,
            actor=actor,
        )
        return _success(
            run={
                "run_id": record.run_id,
                "task_id": record.task_id,
                "executor": record.executor,
                "status": record.status.value,
                "branch": record.branch,
                "commit": record.commit,
                "created_at": str(record.created_at),
            }
        )
    except ValueError as e:
        return _error("VALIDATION_ERROR", str(e))
    except Exception as e:
        return _error("LOG_RUN_ERROR", str(e))


@server.tool(
    name="forgeops_list_runs",
    description="List all execution records (run attempts) for a work item.",
)
def forgeops_list_runs(task_id: int) -> str:
    """List execution records for a work item."""
    try:
        from core.database import get_execution_records

        records = get_execution_records(_get_engine(), task_id)
        return _success(
            runs=[
                {
                    "run_id": r.run_id,
                    "executor": r.executor,
                    "status": r.status.value,
                    "branch": r.branch,
                    "commit": r.commit,
                    "created_at": str(r.created_at),
                }
                for r in records
            ]
        )
    except Exception as e:
        return _error("LIST_RUNS_ERROR", str(e))


# --- Reviews --------------------------------------------------------------


@server.tool(
    name="forgeops_submit_review",
    description="Submit a review for a work item. Decision is 'accepted' or 'rework_required'.",
)
def forgeops_submit_review(
    task_id: int,
    reviewer: str,
    decision: str,
    note: Optional[str] = None,
    actor: Optional[str] = None,
) -> str:
    """Submit a review."""
    try:
        from core.database import create_review, get_work_item
        from models import ReviewDecision

        item = get_work_item(_get_engine(), task_id)
        if not item:
            return _error("NOT_FOUND", f"Work item {task_id} not found")

        review = create_review(
            _get_engine(),
            task_id,
            reviewer,
            ReviewDecision(decision),
            note=note,
            actor=actor,
        )
        return _success(
            review={
                "review_id": review.review_id,
                "task_id": review.task_id,
                "reviewer": review.reviewer,
                "decision": review.decision.value,
                "note": review.note,
                "created_at": str(review.created_at),
            }
        )
    except ValueError as e:
        return _error("VALIDATION_ERROR", str(e))
    except Exception as e:
        return _error("REVIEW_ERROR", str(e))


@server.tool(
    name="forgeops_list_reviews",
    description="List all reviews for a work item.",
)
def forgeops_list_reviews(task_id: int) -> str:
    """List reviews for a work item."""
    try:
        from core.database import get_reviews

        reviews = get_reviews(_get_engine(), task_id)
        return _success(
            reviews=[
                {
                    "review_id": rv.review_id,
                    "reviewer": rv.reviewer,
                    "decision": rv.decision.value,
                    "note": rv.note,
                    "created_at": str(rv.created_at),
                }
                for rv in reviews
            ]
        )
    except Exception as e:
        return _error("LIST_REVIEWS_ERROR", str(e))


# --- Attachments ----------------------------------------------------------


@server.tool(
    name="forgeops_attach",
    description="Attach a URL or file path to a work item.",
)
def forgeops_attach(
    task_id: int,
    url_or_path: str,
    label: Optional[str] = None,
) -> str:
    """Create an attachment."""
    try:
        from core.database import create_attachment, get_work_item

        item = get_work_item(_get_engine(), task_id)
        if not item:
            return _error("NOT_FOUND", f"Work item {task_id} not found")

        att = create_attachment(_get_engine(), task_id, url_or_path, label=label)
        return _success(
            attachment={
                "attachment_id": att.attachment_id,
                "task_id": att.task_id,
                "url_or_path": att.url_or_path,
                "label": att.label,
                "created_at": str(att.created_at),
            }
        )
    except Exception as e:
        return _error("ATTACH_ERROR", str(e))


# --- Repositories ---------------------------------------------------------


@server.tool(
    name="forgeops_list_repos",
    description="List registered repositories.",
)
def forgeops_list_repos(include_archived: bool = False) -> str:
    """List repositories."""
    try:
        from core.database import get_repositories

        repos = get_repositories(_get_engine(), include_archived=include_archived)
        return _success(
            repositories=[
                {
                    "repo_id": r.repo_id,
                    "name": r.name,
                    "org": r.org,
                    "default_branch": r.default_branch,
                    "status": r.status.value,
                    "url": r.url,
                    "description": r.description,
                }
                for r in repos
            ]
        )
    except Exception as e:
        return _error("LIST_REPOS_ERROR", str(e))


@server.tool(
    name="forgeops_add_repo",
    description="Register a new repository in the work ledger.",
)
def forgeops_add_repo(
    name: str,
    org: Optional[str] = None,
    default_branch: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """Add a repository."""
    try:
        from core.database import add_repository

        repo = add_repository(
            _get_engine(),
            name,
            org=org,
            default_branch=default_branch,
            url=url,
            description=description,
        )
        return _success(
            repository={
                "repo_id": repo.repo_id,
                "name": repo.name,
                "org": repo.org,
                "status": repo.status.value,
            }
        )
    except Exception as e:
        return _error("ADD_REPO_ERROR", str(e))


# --- Status & Activity ----------------------------------------------------


@server.tool(
    name="forgeops_status",
    description=(
        "Get a status overview: item counts by state, currently executing items, "
        "blocked items, and items awaiting review."
    ),
)
def forgeops_status() -> str:
    """Status overview."""
    try:
        from core.database import list_work_items

        items = list_work_items(_get_engine())
        by_state = {}
        for item in items:
            by_state.setdefault(item.state.value, []).append(item)

        return _success(
            total=len(items),
            by_state={s: len(v) for s, v in by_state.items()},
            executing=[_serialize_item(i) for i in by_state.get("executing", [])],
            blocked=[_serialize_item(i) for i in items if i.is_blocked],
            awaiting_review=[_serialize_item(i) for i in by_state.get("awaiting_review", [])],
        )
    except Exception as e:
        return _error("STATUS_ERROR", str(e))


@server.tool(
    name="forgeops_activity",
    description="Get the activity log — recent state changes, assignments, reviews, etc.",
)
def forgeops_activity(
    task_id: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Get activity log."""
    try:
        from core.database import get_activity_log

        entries = get_activity_log(_get_engine(), task_id=task_id, limit=limit)
        return _success(
            entries=[
                {
                    "log_id": e.log_id,
                    "task_id": e.task_id,
                    "action": e.action.value,
                    "detail": e.detail,
                    "actor": e.actor,
                    "created_at": str(e.created_at),
                }
                for e in entries
            ]
        )
    except Exception as e:
        return _error("ACTIVITY_ERROR", str(e))


@server.tool(
    name="forgeops_children",
    description="List sub-tasks of a work item with progress rollup (done/total).",
)
def forgeops_children(parent_id: int) -> str:
    """Get children and progress."""
    try:
        from core.database import get_children, get_child_progress

        children = get_children(_get_engine(), parent_id)
        done, total = get_child_progress(_get_engine(), parent_id)
        return _success(
            parent_id=parent_id,
            children=[_serialize_item(c) for c in children],
            progress={"done": done, "total": total},
        )
    except Exception as e:
        return _error("CHILDREN_ERROR", str(e))


# --- Serialization --------------------------------------------------------


def _serialize_item(item) -> dict:
    return {
        "task_id": item.task_id,
        "title": item.title,
        "description": item.description,
        "repository": item.repository.name if item.repository else None,
        "state": item.state.value,
        "priority": item.priority.value,
        "is_blocked": item.is_blocked,
        "blocked_reason": item.blocked_reason,
        "parent_id": item.parent_id,
        "created_by": item.created_by,
        "created_at": str(item.created_at),
        "updated_at": str(item.updated_at),
    }


# --- Entry point ----------------------------------------------------------


def main():
    """Run the ForgeOps MCP server (stdio transport)."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
