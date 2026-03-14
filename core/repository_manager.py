"""Repository Manager - Handles repository validation and management via SQLModel."""

import re

from core.database import (
    add_repository,
    get_repositories,
    get_repository,
    remove_repository,
    update_repository,
)


class RepositoryManager:
    def __init__(self, engine):
        self.engine = engine

    def validate_repo_name(self, repo_name: str) -> tuple[bool, str]:
        if not re.match(r"^[a-zA-Z0-9_-]+$", repo_name):
            return False, "Repository name can only contain letters, numbers, hyphens, and underscores"
        if len(repo_name) < 2:
            return False, "Repository name must be at least 2 characters long"
        if len(repo_name) > 50:
            return False, "Repository name must be 50 characters or less"
        return True, ""

    def load_repositories(self, *, include_archived: bool = False) -> list[str]:
        repos = get_repositories(self.engine, include_archived=include_archived)
        return [r.name for r in repos]

    def suggest_repositories(self, user_input: str) -> tuple[bool, list[str]]:
        repos = self.load_repositories()
        user_lower = user_input.lower()
        suggestions = []
        for repo in repos:
            if repo.lower() == user_lower:
                return True, []
            if user_lower in repo.lower() or repo.lower() in user_lower:
                suggestions.append(repo)
        return False, suggestions

    def add_repository(self, repo_name: str, **kwargs) -> bool:
        existing = get_repository(self.engine, repo_name)
        if existing:
            return False
        add_repository(self.engine, repo_name, **kwargs)
        return True

    def update_repository(self, repo_name: str, **kwargs):
        return update_repository(self.engine, repo_name, **kwargs)

    def remove_repository(self, repo_name: str) -> bool:
        return remove_repository(self.engine, repo_name)

    def get_repository(self, repo_name: str):
        return get_repository(self.engine, repo_name)
