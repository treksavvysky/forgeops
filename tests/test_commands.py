"""Integration tests for CLI commands (Phase 1)."""

import os
import unittest
from io import StringIO
from unittest.mock import patch

from core.database import (
    add_repository,
    create_db_and_tables,
    create_work_item,
    get_repositories,
)
from models import RepoStatus


class CommandTestBase(unittest.TestCase):
    TEST_DB = "test_cmd_phase1.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)
        # Patch create_db_and_tables to return our test engine
        self.patcher = patch("core.database.DB_PATH", self.TEST_DB)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)


class TestListIssuesCommand(CommandTestBase):
    def test_list_issues_shows_items(self):
        add_repository(self.engine, "test-repo")
        create_work_item(self.engine, "First item", repo_name="test-repo")

        from commands.list_issues import list_issues

        with patch("commands.list_issues.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues()
        output = out.getvalue()
        self.assertIn("WI-1", output)
        self.assertIn("First item", output)
        self.assertIn("test-repo", output)

    def test_list_issues_repo_filter(self):
        add_repository(self.engine, "repo-a")
        add_repository(self.engine, "repo-b")
        create_work_item(self.engine, "In A", repo_name="repo-a")
        create_work_item(self.engine, "In B", repo_name="repo-b")

        from commands.list_issues import list_issues

        with patch("commands.list_issues.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues(repo_filter="repo-a")
        output = out.getvalue()
        self.assertIn("In A", output)
        self.assertNotIn("In B", output)

    def test_list_issues_empty(self):
        from commands.list_issues import list_issues

        with patch("commands.list_issues.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues()
        output = out.getvalue()
        self.assertIn("No work items found", output)

    def test_list_issues_state_filter(self):
        from models import WorkItemState

        create_work_item(self.engine, "Queued", state=WorkItemState.queued)
        create_work_item(self.engine, "Closed", state=WorkItemState.closed)

        from commands.list_issues import list_issues

        with patch("commands.list_issues.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues(state_filter="queued")
        output = out.getvalue()
        self.assertIn("Queued", output)
        self.assertNotIn("Closed", output)


class TestViewIssueCommand(CommandTestBase):
    def test_view_existing_item(self):
        add_repository(self.engine, "test-repo")
        create_work_item(self.engine, "Test item", repo_name="test-repo", description="Detailed desc")

        from commands.view_issue import view_issue

        with patch("commands.view_issue.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                view_issue("WI-1")
        output = out.getvalue()
        self.assertIn("Test item", output)
        self.assertIn("test-repo", output)
        self.assertIn("Detailed desc", output)

    def test_view_nonexistent(self):
        from commands.view_issue import view_issue

        with patch("commands.view_issue.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                view_issue("WI-999")
        output = out.getvalue()
        self.assertIn("not found", output)

    def test_view_invalid_id(self):
        from commands.view_issue import view_issue

        with patch("commands.view_issue.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                view_issue("bad-id")
        output = out.getvalue()
        self.assertIn("Invalid", output)

    def test_view_accepts_plain_number(self):
        create_work_item(self.engine, "Plain ID item")

        from commands.view_issue import view_issue

        with patch("commands.view_issue.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                view_issue("1")
        output = out.getvalue()
        self.assertIn("Plain ID item", output)


class TestListReposCommand(CommandTestBase):
    def test_list_repos(self):
        add_repository(self.engine, "alpha")
        add_repository(self.engine, "bravo")

        from commands.list_repos import list_repos

        with patch("commands.list_repos.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_repos()
        output = out.getvalue()
        self.assertIn("alpha", output)
        self.assertIn("bravo", output)

    def test_list_repos_excludes_archived(self):
        add_repository(self.engine, "aaa")
        add_repository(self.engine, "zzz", status=RepoStatus.archived)

        from commands.list_repos import list_repos

        with patch("commands.list_repos.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_repos()
        output = out.getvalue()
        self.assertIn("aaa", output)
        self.assertNotIn("zzz", output)


class TestAddRepoCommand(CommandTestBase):
    def test_add_new_repo(self):
        from commands.add_repo import add_repo

        with patch("commands.add_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                add_repo("new-proj")
        output = out.getvalue()
        self.assertIn("added successfully", output)
        repos = get_repositories(self.engine)
        names = [r.name for r in repos]
        self.assertIn("new-proj", names)

    def test_add_invalid_repo_name(self):
        from commands.add_repo import add_repo

        with patch("commands.add_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                add_repo("bad name!")
        output = out.getvalue()
        self.assertIn("Invalid repository name", output)

    def test_add_duplicate_repo(self):
        add_repository(self.engine, "existing")

        from commands.add_repo import add_repo

        with patch("commands.add_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                add_repo("existing")
        output = out.getvalue()
        self.assertIn("already exists", output)


class TestUpdateRepoCommand(CommandTestBase):
    def test_update_repo(self):
        add_repository(self.engine, "updatable")

        from commands.update_repo import update_repo

        with patch("commands.update_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                update_repo("updatable", org="new-org")
        output = out.getvalue()
        self.assertIn("updated", output)

    def test_update_nonexistent(self):
        from commands.update_repo import update_repo

        with patch("commands.update_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                update_repo("ghost", org="x")
        output = out.getvalue()
        self.assertIn("not found", output)


class TestRemoveRepoCommand(CommandTestBase):
    def test_remove_repo(self):
        add_repository(self.engine, "doomed")

        from commands.remove_repo import remove_repo

        with patch("commands.remove_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                remove_repo("doomed")
        output = out.getvalue()
        self.assertIn("removed", output)

    def test_remove_nonexistent(self):
        from commands.remove_repo import remove_repo

        with patch("commands.remove_repo.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                remove_repo("ghost")
        output = out.getvalue()
        self.assertIn("not found", output)


class TestMigrateCommand(CommandTestBase):
    def test_migrate_imports_legacy_data(self):
        import json
        import shutil

        # Create legacy data
        issues_dir = "test_legacy_issues"
        repos_file = "test_legacy_repos.json"
        os.makedirs(issues_dir, exist_ok=True)
        with open(os.path.join(issues_dir, "ISSUE-001.json"), "w") as f:
            json.dump(
                {
                    "id": "ISSUE-001",
                    "title": "Legacy issue",
                    "description": "From JSON",
                    "repository": "legacy-repo",
                    "created_at": "2026-01-01T00:00:00Z",
                },
                f,
            )
        with open(repos_file, "w") as f:
            json.dump({"repositories": ["legacy-repo"]}, f)

        from commands.migrate_issues import migrate_issues

        with (
            patch("commands.migrate_issues.create_db_and_tables", return_value=self.engine),
            patch("commands.migrate_issues.LEGACY_ISSUES_DIR", issues_dir),
            patch("commands.migrate_issues.LEGACY_REPOS_FILE", repos_file),
            patch("commands.migrate_issues.LEGACY_TASK_LISTS_DIR", "nonexistent"),
        ):
            with patch("sys.stdout", new_callable=StringIO) as out:
                migrate_issues()
        output = out.getvalue()
        self.assertIn("1 repos", output)
        self.assertIn("1 work items", output)

        # Cleanup
        shutil.rmtree(issues_dir)
        os.remove(repos_file)


if __name__ == "__main__":
    unittest.main()
