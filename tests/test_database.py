"""Tests for the new SQLModel-based database layer."""

import os
import unittest

from core.database import (
    add_repository,
    create_db_and_tables,
    create_work_item,
    get_repositories,
    get_repository,
    get_work_item,
    list_work_items,
    remove_repository,
    update_repository,
    update_work_item,
)
from models import Priority, RepoStatus, WorkItemState


class TestDatabaseLayer(unittest.TestCase):
    TEST_DB = "test_phase1.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    # --- Repository -----------------------------------------------------------

    def test_add_and_get_repository(self):
        repo = add_repository(self.engine, "my-repo")
        self.assertEqual(repo.name, "my-repo")
        self.assertEqual(repo.status, RepoStatus.active)

        fetched = get_repository(self.engine, "my-repo")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "my-repo")

    def test_add_repository_with_metadata(self):
        repo = add_repository(
            self.engine,
            "full-repo",
            org="my-org",
            default_branch="main",
            url="https://github.com/test",
            description="A test repo",
        )
        self.assertEqual(repo.org, "my-org")
        self.assertEqual(repo.default_branch, "main")
        self.assertEqual(repo.url, "https://github.com/test")
        self.assertEqual(repo.description, "A test repo")

    def test_add_duplicate_repository_returns_existing(self):
        r1 = add_repository(self.engine, "dup")
        r2 = add_repository(self.engine, "dup")
        self.assertEqual(r1.repo_id, r2.repo_id)

    def test_get_repositories_sorted(self):
        for name in ("charlie", "alpha", "bravo"):
            add_repository(self.engine, name)
        repos = get_repositories(self.engine)
        names = [r.name for r in repos]
        self.assertEqual(names, ["alpha", "bravo", "charlie"])

    def test_get_repositories_excludes_archived(self):
        add_repository(self.engine, "active-repo")
        add_repository(self.engine, "archived-repo", status=RepoStatus.archived)
        active = get_repositories(self.engine, include_archived=False)
        all_repos = get_repositories(self.engine, include_archived=True)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, "active-repo")
        self.assertEqual(len(all_repos), 2)

    def test_update_repository(self):
        add_repository(self.engine, "updatable")
        updated = update_repository(self.engine, "updatable", org="new-org", status=RepoStatus.archived)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.org, "new-org")
        self.assertEqual(updated.status, RepoStatus.archived)

    def test_update_nonexistent_returns_none(self):
        self.assertIsNone(update_repository(self.engine, "ghost", org="x"))

    def test_remove_repository(self):
        add_repository(self.engine, "doomed")
        self.assertTrue(remove_repository(self.engine, "doomed"))
        self.assertIsNone(get_repository(self.engine, "doomed"))

    def test_remove_nonexistent_returns_false(self):
        self.assertFalse(remove_repository(self.engine, "ghost"))

    # --- WorkItem -------------------------------------------------------------

    def test_create_and_get_work_item(self):
        add_repository(self.engine, "test-repo")
        item = create_work_item(self.engine, "My task", repo_name="test-repo")
        self.assertIsNotNone(item.task_id)
        self.assertEqual(item.title, "My task")
        self.assertEqual(item.state, WorkItemState.queued)
        self.assertEqual(item.priority, Priority.medium)

        fetched = get_work_item(self.engine, item.task_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "My task")
        self.assertEqual(fetched.repository.name, "test-repo")

    def test_create_work_item_without_repo(self):
        item = create_work_item(self.engine, "Orphan task")
        self.assertIsNone(item.repo_id)

    def test_create_work_item_with_priority(self):
        item = create_work_item(self.engine, "Urgent task", priority=Priority.urgent)
        self.assertEqual(item.priority, Priority.urgent)

    def test_list_work_items_sorted_by_id(self):
        add_repository(self.engine, "repo")
        for title in ("Third", "First", "Second"):
            create_work_item(self.engine, title, repo_name="repo")
        items = list_work_items(self.engine)
        self.assertEqual(len(items), 3)
        self.assertTrue(items[0].task_id < items[1].task_id < items[2].task_id)

    def test_list_work_items_filter_by_repo(self):
        add_repository(self.engine, "repo-a")
        add_repository(self.engine, "repo-b")
        create_work_item(self.engine, "In A", repo_name="repo-a")
        create_work_item(self.engine, "In B", repo_name="repo-b")
        items = list_work_items(self.engine, repo_name="repo-a")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "In A")

    def test_list_work_items_filter_by_state(self):
        create_work_item(self.engine, "Queued", state=WorkItemState.queued)
        create_work_item(self.engine, "Closed", state=WorkItemState.closed)
        items = list_work_items(self.engine, state=WorkItemState.queued)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Queued")

    def test_list_work_items_filter_by_blocked(self):
        item = create_work_item(self.engine, "Blocked item")
        update_work_item(self.engine, item.task_id, is_blocked=True, blocked_reason="waiting")
        create_work_item(self.engine, "Free item")
        blocked = list_work_items(self.engine, is_blocked=True)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].title, "Blocked item")

    def test_list_work_items_nonexistent_repo_returns_empty(self):
        items = list_work_items(self.engine, repo_name="no-such-repo")
        self.assertEqual(items, [])

    def test_update_work_item(self):
        item = create_work_item(self.engine, "Original")
        updated = update_work_item(self.engine, item.task_id, title="Changed", state=WorkItemState.executing)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, "Changed")
        self.assertEqual(updated.state, WorkItemState.executing)
        self.assertGreater(updated.updated_at, item.created_at)

    def test_update_nonexistent_work_item_returns_none(self):
        self.assertIsNone(update_work_item(self.engine, 9999, title="x"))

    def test_work_item_description_optional(self):
        item = create_work_item(self.engine, "No desc")
        self.assertIsNone(item.description)

    def test_work_item_parent_id(self):
        parent = create_work_item(self.engine, "Parent")
        child = create_work_item(self.engine, "Child", parent_id=parent.task_id)
        self.assertEqual(child.parent_id, parent.task_id)

    def test_get_work_item_nonexistent(self):
        self.assertIsNone(get_work_item(self.engine, 9999))


if __name__ == "__main__":
    unittest.main()
