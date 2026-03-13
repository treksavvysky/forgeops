"""SQLModel-based data access layer for ForgeOps.

Single source of truth — all interfaces (CLI, API) read and write through this module.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, col, create_engine, select

from config import DB_PATH
from models import (
    ActivityAction,
    ActivityLog,
    Assignment,
    Attachment,
    ExecutionRecord,
    ExecutionStatus,
    ExecutorType,
    Priority,
    RepoStatus,
    Repository,
    Review,
    ReviewDecision,
    WorkItem,
    WorkItemState,
)


def get_engine(db_path: Optional[str | Path] = None):
    path = db_path or DB_PATH
    return create_engine(f"sqlite:///{path}", echo=False)


def create_db_and_tables(db_path: Optional[str | Path] = None):
    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)
    return engine


# --- Repository CRUD ----------------------------------------------------------

def add_repository(
    engine,
    name: str,
    *,
    org: Optional[str] = None,
    default_branch: Optional[str] = None,
    status: RepoStatus = RepoStatus.active,
    url: Optional[str] = None,
    description: Optional[str] = None,
) -> Repository:
    with Session(engine) as session:
        existing = session.exec(select(Repository).where(Repository.name == name)).first()
        if existing:
            return existing
        repo = Repository(
            name=name,
            org=org,
            default_branch=default_branch,
            status=status,
            url=url,
            description=description,
        )
        session.add(repo)
        session.commit()
        session.refresh(repo)
        return repo


def get_repository(engine, name: str) -> Optional[Repository]:
    with Session(engine) as session:
        return session.exec(select(Repository).where(Repository.name == name)).first()


def get_repositories(engine, *, include_archived: bool = False) -> list[Repository]:
    with Session(engine) as session:
        stmt = select(Repository).order_by(Repository.name)
        if not include_archived:
            stmt = stmt.where(Repository.status == RepoStatus.active)
        return list(session.exec(stmt).all())


def update_repository(engine, name: str, **kwargs) -> Optional[Repository]:
    with Session(engine) as session:
        repo = session.exec(select(Repository).where(Repository.name == name)).first()
        if not repo:
            return None
        for key, value in kwargs.items():
            if hasattr(repo, key):
                setattr(repo, key, value)
        session.add(repo)
        session.commit()
        session.refresh(repo)
        return repo


def remove_repository(engine, name: str) -> bool:
    with Session(engine) as session:
        repo = session.exec(select(Repository).where(Repository.name == name)).first()
        if not repo:
            return False
        session.delete(repo)
        session.commit()
        return True


# --- WorkItem CRUD ------------------------------------------------------------

def create_work_item(
    engine,
    title: str,
    *,
    repo_name: Optional[str] = None,
    description: Optional[str] = None,
    state: WorkItemState = WorkItemState.queued,
    priority: Priority = Priority.medium,
    parent_id: Optional[int] = None,
    created_by: Optional[str] = None,
) -> WorkItem:
    with Session(engine) as session:
        repo_id = None
        if repo_name:
            repo = session.exec(select(Repository).where(Repository.name == repo_name)).first()
            if repo:
                repo_id = repo.repo_id
        item = WorkItem(
            title=title,
            repo_id=repo_id,
            description=description,
            state=state,
            priority=priority,
            parent_id=parent_id,
            created_by=created_by,
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        _log_activity(session, item.task_id, ActivityAction.created,
                      detail=f"Created in state {state.value}", actor=created_by)
        session.refresh(item)
        return item


def get_work_item(engine, task_id: int) -> Optional[WorkItem]:
    with Session(engine) as session:
        stmt = (
            select(WorkItem)
            .where(WorkItem.task_id == task_id)
            .options(selectinload(WorkItem.repository))  # type: ignore[arg-type]
        )
        return session.exec(stmt).first()


def list_work_items(
    engine,
    *,
    repo_name: Optional[str] = None,
    state: Optional[WorkItemState] = None,
    is_blocked: Optional[bool] = None,
    priority: Optional[Priority] = None,
    parent_id: Optional[int] = None,
) -> list[WorkItem]:
    with Session(engine) as session:
        stmt = (
            select(WorkItem)
            .options(selectinload(WorkItem.repository))  # type: ignore[arg-type]
            .order_by(WorkItem.task_id)
        )
        if repo_name:
            repo = session.exec(select(Repository).where(Repository.name == repo_name)).first()
            if repo:
                stmt = stmt.where(WorkItem.repo_id == repo.repo_id)
            else:
                return []
        if state:
            stmt = stmt.where(WorkItem.state == state)
        if is_blocked is not None:
            stmt = stmt.where(WorkItem.is_blocked == is_blocked)
        if priority:
            stmt = stmt.where(WorkItem.priority == priority)
        if parent_id is not None:
            stmt = stmt.where(WorkItem.parent_id == parent_id)
        return list(session.exec(stmt).all())


def update_work_item(engine, task_id: int, **kwargs) -> Optional[WorkItem]:
    with Session(engine) as session:
        item = session.get(WorkItem, task_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        item.updated_at = datetime.now(UTC)
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


def transition_work_item(
    engine,
    task_id: int,
    new_state: WorkItemState,
    *,
    actor: Optional[str] = None,
) -> WorkItem:
    """Transition a work item to a new state with validation and concurrency guard."""
    from core.state_engine import validate_transition, check_repo_concurrency
    from core.hooks import hooks, HookEvent

    with Session(engine) as session:
        item = session.get(WorkItem, task_id)
        if not item:
            raise ValueError(f"Work item {task_id} not found")

        old_state = item.state
        validate_transition(old_state, new_state)

        if new_state == WorkItemState.executing:
            try:
                check_repo_concurrency(engine, item.repo_id, task_id)
            except Exception as e:
                hooks.fire(HookEvent.on_repo_conflict, {
                    "task_id": task_id, "repo_id": item.repo_id, "error": str(e),
                })
                raise

        item.state = new_state
        item.updated_at = datetime.now(UTC)
        session.add(item)
        session.commit()

        _log_activity(session, task_id, ActivityAction.state_change,
                      detail=f"{old_state.value} → {new_state.value}", actor=actor)
        session.refresh(item)

    # Fire hooks after session is committed
    hooks.fire(HookEvent.on_state_change, {
        "task_id": task_id, "old_state": old_state.value, "new_state": new_state.value, "actor": actor,
    })
    if new_state == WorkItemState.completed:
        hooks.fire(HookEvent.on_execution_complete, {"task_id": task_id, "actor": actor})
    if new_state == WorkItemState.rework_required:
        hooks.fire(HookEvent.on_rework, {"task_id": task_id, "actor": actor})

    return item


def block_work_item(engine, task_id: int, reason: str, *, actor: Optional[str] = None) -> WorkItem:
    from core.hooks import hooks, HookEvent

    with Session(engine) as session:
        item = session.get(WorkItem, task_id)
        if not item:
            raise ValueError(f"Work item {task_id} not found")
        item.is_blocked = True
        item.blocked_reason = reason
        item.updated_at = datetime.now(UTC)
        session.add(item)
        session.commit()

        _log_activity(session, task_id, ActivityAction.blocked,
                      detail=reason, actor=actor)
        session.refresh(item)

    hooks.fire(HookEvent.on_blocked, {"task_id": task_id, "reason": reason, "actor": actor})
    return item


def unblock_work_item(engine, task_id: int, *, actor: Optional[str] = None) -> WorkItem:
    from core.hooks import hooks, HookEvent

    with Session(engine) as session:
        item = session.get(WorkItem, task_id)
        if not item:
            raise ValueError(f"Work item {task_id} not found")
        item.is_blocked = False
        item.blocked_reason = None
        item.updated_at = datetime.now(UTC)
        session.add(item)
        session.commit()

        _log_activity(session, task_id, ActivityAction.unblocked, actor=actor)
        session.refresh(item)

    hooks.fire(HookEvent.on_unblocked, {"task_id": task_id, "actor": actor})
    return item


def get_children(engine, parent_id: int) -> list[WorkItem]:
    return list_work_items(engine, parent_id=parent_id)


def get_child_progress(engine, parent_id: int) -> tuple[int, int]:
    """Return (completed_count, total_count) for children of a work item."""
    children = get_children(engine, parent_id)
    if not children:
        return 0, 0
    closed_states = {WorkItemState.accepted, WorkItemState.closed}
    done = sum(1 for c in children if c.state in closed_states)
    return done, len(children)


# --- Assignment CRUD ----------------------------------------------------------

def create_assignment(
    engine,
    task_id: int,
    executor: str,
    executor_type: ExecutorType,
    *,
    actor: Optional[str] = None,
) -> Assignment:
    from core.hooks import hooks, HookEvent

    with Session(engine) as session:
        assignment = Assignment(
            task_id=task_id,
            executor=executor,
            executor_type=executor_type,
        )
        session.add(assignment)
        session.commit()

        _log_activity(session, task_id, ActivityAction.assigned,
                      detail=f"{executor} ({executor_type.value})", actor=actor)
        session.refresh(assignment)

    hooks.fire(HookEvent.on_assigned, {
        "task_id": task_id, "executor": executor,
        "executor_type": executor_type.value, "actor": actor,
    })
    return assignment


def get_assignments(engine, task_id: int) -> list[Assignment]:
    with Session(engine) as session:
        stmt = select(Assignment).where(Assignment.task_id == task_id).order_by(Assignment.assigned_at)
        return list(session.exec(stmt).all())


def get_current_assignment(engine, task_id: int) -> Optional[Assignment]:
    with Session(engine) as session:
        stmt = (
            select(Assignment)
            .where(Assignment.task_id == task_id)
            .order_by(col(Assignment.assigned_at).desc())
        )
        return session.exec(stmt).first()


def list_items_by_executor(engine, executor: str) -> list[WorkItem]:
    """Get work items currently assigned to an executor (latest assignment wins)."""
    with Session(engine) as session:
        # Get all assignments for this executor
        stmt = select(Assignment).where(Assignment.executor == executor)
        assignments = session.exec(stmt).all()
        task_ids = {a.task_id for a in assignments}
        if not task_ids:
            return []
        # Filter to only items where this executor is the *latest* assignment
        result = []
        for tid in task_ids:
            latest = session.exec(
                select(Assignment)
                .where(Assignment.task_id == tid)
                .order_by(col(Assignment.assigned_at).desc())
            ).first()
            if latest and latest.executor == executor:
                item = session.exec(
                    select(WorkItem)
                    .where(WorkItem.task_id == tid)
                    .options(selectinload(WorkItem.repository))  # type: ignore[arg-type]
                ).first()
                if item:
                    result.append(item)
        result.sort(key=lambda x: x.task_id)
        return result


# --- ExecutionRecord CRUD -----------------------------------------------------

def create_execution_record(
    engine,
    task_id: int,
    executor: str,
    status: ExecutionStatus,
    *,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
    logs_ref: Optional[str] = None,
    artifact_ref: Optional[str] = None,
    actor: Optional[str] = None,
) -> ExecutionRecord:
    with Session(engine) as session:
        record = ExecutionRecord(
            task_id=task_id,
            executor=executor,
            status=status,
            branch=branch,
            commit=commit,
            logs_ref=logs_ref,
            artifact_ref=artifact_ref,
        )
        session.add(record)
        session.commit()

        _log_activity(session, task_id, ActivityAction.execution_logged,
                      detail=f"{status.value} by {executor}", actor=actor)
        session.refresh(record)
        return record


def get_execution_records(engine, task_id: int) -> list[ExecutionRecord]:
    with Session(engine) as session:
        stmt = select(ExecutionRecord).where(ExecutionRecord.task_id == task_id).order_by(ExecutionRecord.created_at)
        return list(session.exec(stmt).all())


# --- Review CRUD --------------------------------------------------------------

def create_review(
    engine,
    task_id: int,
    reviewer: str,
    decision: ReviewDecision,
    *,
    note: Optional[str] = None,
    actor: Optional[str] = None,
) -> Review:
    from core.hooks import hooks, HookEvent

    with Session(engine) as session:
        review = Review(
            task_id=task_id,
            reviewer=reviewer,
            decision=decision,
            note=note,
        )
        session.add(review)
        session.commit()

        _log_activity(session, task_id, ActivityAction.review_submitted,
                      detail=f"{decision.value} by {reviewer}", actor=actor)
        session.refresh(review)

    hooks.fire(HookEvent.on_review_submitted, {
        "task_id": task_id, "reviewer": reviewer,
        "decision": decision.value, "note": note, "actor": actor,
    })
    return review


def get_reviews(engine, task_id: int) -> list[Review]:
    with Session(engine) as session:
        stmt = select(Review).where(Review.task_id == task_id).order_by(Review.created_at)
        return list(session.exec(stmt).all())


# --- Attachment CRUD ----------------------------------------------------------

def create_attachment(engine, task_id: int, url_or_path: str, *, label: Optional[str] = None) -> Attachment:
    with Session(engine) as session:
        att = Attachment(task_id=task_id, url_or_path=url_or_path, label=label)
        session.add(att)
        session.commit()
        session.refresh(att)
        return att


def get_attachments(engine, task_id: int) -> list[Attachment]:
    with Session(engine) as session:
        stmt = select(Attachment).where(Attachment.task_id == task_id).order_by(Attachment.created_at)
        return list(session.exec(stmt).all())


# --- Activity Log -------------------------------------------------------------

def _log_activity(
    session: Session,
    task_id: Optional[int],
    action: ActivityAction,
    *,
    detail: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Append an entry to the activity log. Called within an existing session."""
    entry = ActivityLog(task_id=task_id, action=action, detail=detail, actor=actor)
    session.add(entry)
    session.commit()


def get_activity_log(engine, *, task_id: Optional[int] = None, limit: int = 50) -> list[ActivityLog]:
    with Session(engine) as session:
        stmt = select(ActivityLog).order_by(col(ActivityLog.created_at).desc())
        if task_id is not None:
            stmt = stmt.where(ActivityLog.task_id == task_id)
        stmt = stmt.limit(limit)
        return list(session.exec(stmt).all())
