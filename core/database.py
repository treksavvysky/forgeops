"""SQLModel-based data access layer for ForgeOps.

Single source of truth — replaces the old dual-storage (JSON + raw sqlite3) model.
All interfaces (CLI, API) read and write through this module.
"""

from pathlib import Path
from typing import Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, create_engine, select

from config import DB_PATH
from models import Priority, RepoStatus, Repository, WorkItem, WorkItemState


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
    include_archived_repos: bool = False,
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
        return list(session.exec(stmt).all())


def update_work_item(engine, task_id: int, **kwargs) -> Optional[WorkItem]:
    from datetime import UTC, datetime

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
