"""ForgeOps REST API — full CRUD for the work ledger.

Covers: work items, repositories, assignments, execution records, reviews,
attachments, activity log, and status overview.
"""

import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel

from core.database import (
    add_repository,
    block_work_item,
    create_assignment,
    create_attachment,
    create_db_and_tables,
    create_execution_record,
    create_review,
    create_work_item,
    get_activity_log,
    get_assignments,
    get_attachments,
    get_child_progress,
    get_children,
    get_current_assignment,
    get_execution_records,
    get_repositories,
    get_repository,
    get_reviews,
    get_work_item,
    list_items_by_executor,
    list_work_items,
    remove_repository,
    transition_work_item,
    unblock_work_item,
    update_repository,
    update_work_item,
)
from core.state_engine import InvalidTransitionError, RepoConcurrencyError
from models import (
    ExecutionStatus,
    ExecutorType,
    Priority,
    ReviewDecision,
    WorkItemState,
)

app = FastAPI(title="ForgeOps Work Ledger API", version="0.3.0")

engine = create_db_and_tables()

# --- Auth -----------------------------------------------------------------

API_BEARER_TOKEN = os.environ.get("API_BEARER_TOKEN")


def verify_token(authorization: Optional[str] = Header(None)):
    """Bearer token auth. Skipped if API_BEARER_TOKEN is not set."""
    if not API_BEARER_TOKEN:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != API_BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bearer token")


# --- Request schemas ------------------------------------------------------


class WorkItemCreate(BaseModel):
    title: str
    repo_name: Optional[str] = None
    description: Optional[str] = None
    state: WorkItemState = WorkItemState.queued
    priority: Priority = Priority.medium
    parent_id: Optional[int] = None
    created_by: Optional[str] = None


class WorkItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None


class WorkItemTransition(BaseModel):
    state: WorkItemState
    actor: Optional[str] = None


class BlockRequest(BaseModel):
    reason: str
    actor: Optional[str] = None


class UnblockRequest(BaseModel):
    actor: Optional[str] = None


class RepositoryCreate(BaseModel):
    name: str
    org: Optional[str] = None
    default_branch: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


class RepositoryUpdate(BaseModel):
    org: Optional[str] = None
    default_branch: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


class AssignmentCreate(BaseModel):
    executor: str
    executor_type: ExecutorType = ExecutorType.human
    actor: Optional[str] = None


class ExecutionRecordCreate(BaseModel):
    executor: str
    status: ExecutionStatus
    branch: Optional[str] = None
    commit: Optional[str] = None
    logs_ref: Optional[str] = None
    artifact_ref: Optional[str] = None
    actor: Optional[str] = None


class ReviewCreate(BaseModel):
    reviewer: str
    decision: ReviewDecision
    note: Optional[str] = None
    actor: Optional[str] = None


class AttachmentCreate(BaseModel):
    url_or_path: str
    label: Optional[str] = None


# --- Serialization helpers ------------------------------------------------


def _serialize_work_item(item):
    return {
        "task_id": item.task_id,
        "repo_id": item.repo_id,
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


def _serialize_repo(r):
    return {
        "repo_id": r.repo_id,
        "name": r.name,
        "org": r.org,
        "default_branch": r.default_branch,
        "status": r.status.value,
        "url": r.url,
        "description": r.description,
    }


def _serialize_assignment(a):
    return {
        "assignment_id": a.assignment_id,
        "task_id": a.task_id,
        "executor": a.executor,
        "executor_type": a.executor_type.value,
        "assigned_at": str(a.assigned_at),
    }


def _serialize_execution_record(r):
    return {
        "run_id": r.run_id,
        "task_id": r.task_id,
        "executor": r.executor,
        "branch": r.branch,
        "commit": r.commit,
        "status": r.status.value,
        "logs_ref": r.logs_ref,
        "artifact_ref": r.artifact_ref,
        "created_at": str(r.created_at),
    }


def _serialize_review(rv):
    return {
        "review_id": rv.review_id,
        "task_id": rv.task_id,
        "reviewer": rv.reviewer,
        "decision": rv.decision.value,
        "note": rv.note,
        "created_at": str(rv.created_at),
    }


def _serialize_attachment(att):
    return {
        "attachment_id": att.attachment_id,
        "task_id": att.task_id,
        "url_or_path": att.url_or_path,
        "label": att.label,
        "created_at": str(att.created_at),
    }


def _serialize_activity(entry):
    return {
        "log_id": entry.log_id,
        "task_id": entry.task_id,
        "action": entry.action.value,
        "detail": entry.detail,
        "actor": entry.actor,
        "created_at": str(entry.created_at),
    }


# --- Work Items -----------------------------------------------------------


@app.get("/work-items")
def list_work_items_endpoint(
    repo: Optional[str] = None,
    state: Optional[WorkItemState] = None,
    priority: Optional[Priority] = None,
    is_blocked: Optional[bool] = None,
    parent_id: Optional[int] = None,
    _=Depends(verify_token),
):
    items = list_work_items(
        engine,
        repo_name=repo,
        state=state,
        priority=priority,
        is_blocked=is_blocked,
        parent_id=parent_id,
    )
    return [_serialize_work_item(i) for i in items]


@app.post("/work-items", status_code=201)
def create_work_item_endpoint(body: WorkItemCreate, _=Depends(verify_token)):
    item = create_work_item(
        engine,
        body.title,
        repo_name=body.repo_name,
        description=body.description,
        state=body.state,
        priority=body.priority,
        parent_id=body.parent_id,
        created_by=body.created_by,
    )
    return _serialize_work_item(get_work_item(engine, item.task_id))


@app.get("/work-items/{task_id}")
def get_work_item_endpoint(task_id: int, _=Depends(verify_token)):
    item = get_work_item(engine, task_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Work item {task_id} not found")
    return _serialize_work_item(item)


@app.patch("/work-items/{task_id}")
def update_work_item_endpoint(task_id: int, body: WorkItemUpdate, _=Depends(verify_token)):
    kwargs = body.model_dump(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    item = update_work_item(engine, task_id, **kwargs)
    if not item:
        raise HTTPException(status_code=404, detail=f"Work item {task_id} not found")
    return _serialize_work_item(get_work_item(engine, item.task_id))


@app.post("/work-items/{task_id}/transition")
def transition_work_item_endpoint(task_id: int, body: WorkItemTransition, _=Depends(verify_token)):
    try:
        item = transition_work_item(engine, task_id, body.state, actor=body.actor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RepoConcurrencyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _serialize_work_item(get_work_item(engine, item.task_id))


@app.post("/work-items/{task_id}/block")
def block_work_item_endpoint(task_id: int, body: BlockRequest, _=Depends(verify_token)):
    try:
        item = block_work_item(engine, task_id, body.reason, actor=body.actor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _serialize_work_item(get_work_item(engine, item.task_id))


@app.post("/work-items/{task_id}/unblock")
def unblock_work_item_endpoint(task_id: int, body: UnblockRequest = UnblockRequest(), _=Depends(verify_token)):
    try:
        item = unblock_work_item(engine, task_id, actor=body.actor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _serialize_work_item(get_work_item(engine, item.task_id))


@app.get("/work-items/{task_id}/children")
def get_children_endpoint(task_id: int, _=Depends(verify_token)):
    children = get_children(engine, task_id)
    done, total = get_child_progress(engine, task_id)
    return {
        "parent_id": task_id,
        "children": [_serialize_work_item(c) for c in children],
        "progress": {"done": done, "total": total},
    }


# --- Repositories ---------------------------------------------------------


@app.get("/repositories")
def list_repositories_endpoint(include_archived: bool = False, _=Depends(verify_token)):
    repos = get_repositories(engine, include_archived=include_archived)
    return [_serialize_repo(r) for r in repos]


@app.post("/repositories", status_code=201)
def create_repository_endpoint(body: RepositoryCreate, _=Depends(verify_token)):
    repo = add_repository(
        engine,
        body.name,
        org=body.org,
        default_branch=body.default_branch,
        url=body.url,
        description=body.description,
    )
    return _serialize_repo(repo)


@app.get("/repositories/{name}")
def get_repository_endpoint(name: str, _=Depends(verify_token)):
    repo = get_repository(engine, name)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{name}' not found")
    return _serialize_repo(repo)


@app.patch("/repositories/{name}")
def update_repository_endpoint(name: str, body: RepositoryUpdate, _=Depends(verify_token)):
    kwargs = body.model_dump(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    repo = update_repository(engine, name, **kwargs)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{name}' not found")
    return _serialize_repo(repo)


@app.delete("/repositories/{name}", status_code=204)
def delete_repository_endpoint(name: str, _=Depends(verify_token)):
    if not remove_repository(engine, name):
        raise HTTPException(status_code=404, detail=f"Repository '{name}' not found")


# --- Assignments ----------------------------------------------------------


@app.get("/work-items/{task_id}/assignments")
def list_assignments_endpoint(task_id: int, _=Depends(verify_token)):
    return [_serialize_assignment(a) for a in get_assignments(engine, task_id)]


@app.post("/work-items/{task_id}/assignments", status_code=201)
def create_assignment_endpoint(task_id: int, body: AssignmentCreate, _=Depends(verify_token)):
    item = get_work_item(engine, task_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Work item {task_id} not found")
    assignment = create_assignment(engine, task_id, body.executor, body.executor_type, actor=body.actor)
    return _serialize_assignment(assignment)


@app.get("/work-items/{task_id}/assignments/current")
def get_current_assignment_endpoint(task_id: int, _=Depends(verify_token)):
    assignment = get_current_assignment(engine, task_id)
    if not assignment:
        raise HTTPException(status_code=404, detail=f"No assignment for work item {task_id}")
    return _serialize_assignment(assignment)


@app.get("/executors/{executor}/work-items")
def list_executor_work_items(executor: str, _=Depends(verify_token)):
    items = list_items_by_executor(engine, executor)
    return [_serialize_work_item(i) for i in items]


# --- Execution Records ----------------------------------------------------


@app.get("/work-items/{task_id}/runs")
def list_runs_endpoint(task_id: int, _=Depends(verify_token)):
    return [_serialize_execution_record(r) for r in get_execution_records(engine, task_id)]


@app.post("/work-items/{task_id}/runs", status_code=201)
def create_run_endpoint(task_id: int, body: ExecutionRecordCreate, _=Depends(verify_token)):
    item = get_work_item(engine, task_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Work item {task_id} not found")
    record = create_execution_record(
        engine,
        task_id,
        body.executor,
        body.status,
        branch=body.branch,
        commit=body.commit,
        logs_ref=body.logs_ref,
        artifact_ref=body.artifact_ref,
        actor=body.actor,
    )
    return _serialize_execution_record(record)


# --- Reviews --------------------------------------------------------------


@app.get("/work-items/{task_id}/reviews")
def list_reviews_endpoint(task_id: int, _=Depends(verify_token)):
    return [_serialize_review(rv) for rv in get_reviews(engine, task_id)]


@app.post("/work-items/{task_id}/reviews", status_code=201)
def create_review_endpoint(task_id: int, body: ReviewCreate, _=Depends(verify_token)):
    item = get_work_item(engine, task_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Work item {task_id} not found")
    review = create_review(
        engine,
        task_id,
        body.reviewer,
        body.decision,
        note=body.note,
        actor=body.actor,
    )
    return _serialize_review(review)


# --- Attachments ----------------------------------------------------------


@app.get("/work-items/{task_id}/attachments")
def list_attachments_endpoint(task_id: int, _=Depends(verify_token)):
    return [_serialize_attachment(att) for att in get_attachments(engine, task_id)]


@app.post("/work-items/{task_id}/attachments", status_code=201)
def create_attachment_endpoint(task_id: int, body: AttachmentCreate, _=Depends(verify_token)):
    item = get_work_item(engine, task_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Work item {task_id} not found")
    att = create_attachment(engine, task_id, body.url_or_path, label=body.label)
    return _serialize_attachment(att)


# --- Activity Log & Status ------------------------------------------------


@app.get("/activity")
def get_activity_endpoint(
    task_id: Optional[int] = None,
    limit: int = 50,
    _=Depends(verify_token),
):
    entries = get_activity_log(engine, task_id=task_id, limit=limit)
    return [_serialize_activity(e) for e in entries]


@app.get("/status")
def status_overview_endpoint(_=Depends(verify_token)):
    all_items = list_work_items(engine)
    by_state = {}
    for item in all_items:
        by_state.setdefault(item.state.value, []).append(item)

    return {
        "total": len(all_items),
        "by_state": {state: len(items) for state, items in by_state.items()},
        "executing": [_serialize_work_item(i) for i in by_state.get("executing", [])],
        "blocked": [_serialize_work_item(i) for i in all_items if i.is_blocked],
        "awaiting_review": [_serialize_work_item(i) for i in by_state.get("awaiting_review", [])],
    }


# --- Legacy aliases (backwards compat) ------------------------------------


@app.get("/issues")
def get_issues_legacy(
    repo: Optional[str] = None,
    state: Optional[WorkItemState] = None,
    _=Depends(verify_token),
):
    """Legacy endpoint — use /work-items instead."""
    items = list_work_items(engine, repo_name=repo, state=state)
    return [_serialize_work_item(i) for i in items]
