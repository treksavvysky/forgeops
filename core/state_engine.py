"""State engine — transition validation and repo concurrency guard.

The lifecycle:
  queued → assigned → executing → completed → awaiting_review → accepted → closed
                          ↑                                        │
                          └──────── rework_required ───────────────┘

Key rules:
  - Only valid transitions are allowed (see TRANSITIONS).
  - Block mechanism is orthogonal — any state can be blocked/unblocked.
  - Repo concurrency guard: one executing item per repo_id at a time.
"""

from models import WorkItemState

# Valid transitions: from_state → set of allowed to_states
TRANSITIONS: dict[WorkItemState, set[WorkItemState]] = {
    WorkItemState.queued: {WorkItemState.assigned, WorkItemState.closed},
    WorkItemState.assigned: {WorkItemState.executing, WorkItemState.queued, WorkItemState.closed},
    WorkItemState.executing: {WorkItemState.completed, WorkItemState.assigned, WorkItemState.closed},
    WorkItemState.completed: {WorkItemState.awaiting_review, WorkItemState.closed},
    WorkItemState.awaiting_review: {WorkItemState.accepted, WorkItemState.rework_required, WorkItemState.closed},
    WorkItemState.accepted: {WorkItemState.closed},
    WorkItemState.rework_required: {WorkItemState.executing, WorkItemState.closed},
    WorkItemState.closed: set(),
}


class InvalidTransitionError(Exception):
    def __init__(self, from_state: WorkItemState, to_state: WorkItemState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition: {from_state.value} → {to_state.value}. "
            f"Allowed from {from_state.value}: {', '.join(s.value for s in TRANSITIONS[from_state]) or 'none'}"
        )


class RepoConcurrencyError(Exception):
    def __init__(self, repo_name: str, blocking_task_id: int):
        self.repo_name = repo_name
        self.blocking_task_id = blocking_task_id
        super().__init__(
            f"Repository '{repo_name}' already has an item in executing state (WI-{blocking_task_id}). "
            f"Only one work item per repository may be executing at a time."
        )


def validate_transition(from_state: WorkItemState, to_state: WorkItemState) -> None:
    allowed = TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise InvalidTransitionError(from_state, to_state)


def check_repo_concurrency(engine, repo_id: int | None, task_id: int) -> None:
    """Raise RepoConcurrencyError if another item for the same repo is already executing."""
    if repo_id is None:
        return

    from sqlmodel import Session, select
    from models import WorkItem, Repository

    with Session(engine) as session:
        stmt = (
            select(WorkItem)
            .where(WorkItem.repo_id == repo_id)
            .where(WorkItem.state == WorkItemState.executing)
            .where(WorkItem.task_id != task_id)
        )
        blocking = session.exec(stmt).first()
        if blocking:
            repo = session.get(Repository, repo_id)
            repo_name = repo.name if repo else f"repo_id={repo_id}"
            raise RepoConcurrencyError(repo_name, blocking.task_id)
