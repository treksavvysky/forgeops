"""SQLModel / Pydantic models for the ForgeOps work ledger.

Defines the five core objects from the target data model:
  Repository, WorkItem, Assignment, ExecutionRecord, Review
"""

import enum
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


# --- Enums -------------------------------------------------------------------

class RepoStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class WorkItemState(str, enum.Enum):
    queued = "queued"
    assigned = "assigned"
    executing = "executing"
    completed = "completed"
    awaiting_review = "awaiting_review"
    accepted = "accepted"
    rework_required = "rework_required"
    closed = "closed"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ExecutorType(str, enum.Enum):
    human = "human"
    agent = "agent"


class ExecutionStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    partial = "partial"


class ReviewDecision(str, enum.Enum):
    accepted = "accepted"
    rework_required = "rework_required"


# --- Repository ---------------------------------------------------------------

class Repository(SQLModel, table=True):
    __tablename__ = "repositories"

    repo_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    org: Optional[str] = None
    default_branch: Optional[str] = None
    status: RepoStatus = Field(default=RepoStatus.active)
    url: Optional[str] = None
    description: Optional[str] = None

    work_items: list["WorkItem"] = Relationship(back_populates="repository")


# --- WorkItem -----------------------------------------------------------------

class WorkItem(SQLModel, table=True):
    __tablename__ = "work_items"

    task_id: Optional[int] = Field(default=None, primary_key=True)
    repo_id: Optional[int] = Field(default=None, foreign_key="repositories.repo_id", index=True)
    title: str
    description: Optional[str] = None
    state: WorkItemState = Field(default=WorkItemState.queued, index=True)
    priority: Priority = Field(default=Priority.medium)
    is_blocked: bool = Field(default=False)
    blocked_reason: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, foreign_key="work_items.task_id")
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    repository: Optional[Repository] = Relationship(back_populates="work_items")


# --- Assignment ---------------------------------------------------------------

class Assignment(SQLModel, table=True):
    __tablename__ = "assignments"

    assignment_id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="work_items.task_id", index=True)
    executor: str
    executor_type: ExecutorType
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# --- ExecutionRecord ----------------------------------------------------------

class ExecutionRecord(SQLModel, table=True):
    __tablename__ = "execution_records"

    run_id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="work_items.task_id", index=True)
    executor: str
    branch: Optional[str] = None
    commit: Optional[str] = None
    status: ExecutionStatus
    logs_ref: Optional[str] = None
    artifact_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# --- Review -------------------------------------------------------------------

class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    review_id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="work_items.task_id", index=True)
    reviewer: str
    decision: ReviewDecision
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
