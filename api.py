"""ForgeOps REST API — read endpoints for the work ledger."""

from typing import Optional

from fastapi import FastAPI

from core.database import create_db_and_tables, get_repositories, list_work_items
from models import WorkItemState

app = FastAPI(title="ForgeOps Work Ledger API")

engine = create_db_and_tables()


@app.get("/issues")
def get_issues(
    repo: Optional[str] = None,
    state: Optional[WorkItemState] = None,
):
    items = list_work_items(engine, repo_name=repo, state=state)
    return [
        {
            "task_id": item.task_id,
            "title": item.title,
            "description": item.description,
            "repository": item.repository.name if item.repository else None,
            "state": item.state.value,
            "priority": item.priority.value,
            "is_blocked": item.is_blocked,
            "blocked_reason": item.blocked_reason,
            "created_by": item.created_by,
            "created_at": str(item.created_at),
            "updated_at": str(item.updated_at),
        }
        for item in items
    ]


@app.get("/repositories")
def get_repos(include_archived: bool = False):
    repos = get_repositories(engine, include_archived=include_archived)
    return [
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
