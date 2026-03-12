import json
import os
import shutil
import unittest
from io import StringIO
from unittest.mock import patch

from core.db import Database
from core.file_manager import FileManager


class CommandTestBase(unittest.TestCase):
    """Shared setup for command integration tests."""

    TEST_ISSUES_DIR = "test_cmd_issues"
    TEST_COUNTER_FILE = "test_cmd_counter.txt"
    TEST_REPOS_FILE = "test_cmd_repos.json"
    TEST_DB_PATH = "test_cmd.db"

    def setUp(self):
        self._cleanup()
        # Prepare a known issue on disk
        self.fm = FileManager(
            issues_dir=self.TEST_ISSUES_DIR,
            counter_file=self.TEST_COUNTER_FILE,
        )
        self.db = Database(db_path=self.TEST_DB_PATH)
        self.sample_issue = {
            "id": "ISSUE-001",
            "title": "First issue",
            "description": "A test issue",
            "repository": "test-repo",
            "created_at": "2026-01-15T10:30:00Z",
        }
        self.fm.save_issue(self.sample_issue)
        self.db.add_issue(self.sample_issue)
        self.db.add_repository("test-repo")

    def tearDown(self):
        self.db.close()
        self._cleanup()

    def _cleanup(self):
        for d in (self.TEST_ISSUES_DIR,):
            if os.path.isdir(d):
                shutil.rmtree(d)
        for f in (self.TEST_COUNTER_FILE, self.TEST_REPOS_FILE, self.TEST_DB_PATH):
            if os.path.isfile(f):
                os.remove(f)


class TestListIssuesCommand(CommandTestBase):

    def test_list_issues_shows_issue(self):
        from commands.list_issues import list_issues

        with patch("commands.list_issues.FileManager") as MockFM:
            MockFM.return_value = self.fm
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues()
        output = out.getvalue()
        self.assertIn("ISSUE-001", output)
        self.assertIn("First issue", output)
        self.assertIn("test-repo", output)

    def test_list_issues_repo_filter(self):
        # Add a second issue in a different repo
        issue2 = {
            "id": "ISSUE-002",
            "title": "Other issue",
            "description": "",
            "repository": "other-repo",
            "created_at": "2026-01-16T00:00:00Z",
        }
        self.fm.save_issue(issue2)

        from commands.list_issues import list_issues

        with patch("commands.list_issues.FileManager") as MockFM:
            MockFM.return_value = self.fm
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues(repo_filter="test-repo")
        output = out.getvalue()
        self.assertIn("ISSUE-001", output)
        self.assertNotIn("ISSUE-002", output)

    def test_list_issues_empty(self):
        # Use a fresh empty FileManager
        empty_fm = FileManager(
            issues_dir=self.TEST_ISSUES_DIR + "_empty",
            counter_file=self.TEST_COUNTER_FILE,
        )
        from commands.list_issues import list_issues

        with patch("commands.list_issues.FileManager") as MockFM:
            MockFM.return_value = empty_fm
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_issues()
        output = out.getvalue()
        self.assertIn("No issues found", output)
        # Cleanup the extra dir
        if os.path.isdir(self.TEST_ISSUES_DIR + "_empty"):
            shutil.rmtree(self.TEST_ISSUES_DIR + "_empty")


class TestViewIssueCommand(CommandTestBase):

    def test_view_existing_issue(self):
        from commands.view_issue import view_issue

        with patch("commands.view_issue.FileManager") as MockFM:
            MockFM.return_value = self.fm
            with patch("sys.stdout", new_callable=StringIO) as out:
                view_issue("ISSUE-001")
        output = out.getvalue()
        self.assertIn("First issue", output)
        self.assertIn("test-repo", output)
        self.assertIn("A test issue", output)

    def test_view_nonexistent_issue(self):
        from commands.view_issue import view_issue

        with patch("commands.view_issue.FileManager") as MockFM:
            MockFM.return_value = self.fm
            with patch("sys.stdout", new_callable=StringIO) as out:
                view_issue("ISSUE-999")
        output = out.getvalue()
        self.assertIn("not found", output)

    def test_view_invalid_id_format(self):
        from commands.view_issue import view_issue

        with patch("sys.stdout", new_callable=StringIO) as out:
            view_issue("bad-id")
        output = out.getvalue()
        self.assertIn("Invalid issue ID format", output)


class TestListReposCommand(CommandTestBase):

    def test_list_repos(self):
        # Write a known repos file
        with open(self.TEST_REPOS_FILE, "w") as f:
            json.dump({"repositories": ["alpha", "bravo"]}, f)

        from commands.list_repos import list_repos

        with patch("commands.list_repos.RepositoryManager") as MockRM:
            from core.repository_manager import RepositoryManager

            rm = RepositoryManager(repos_file=self.TEST_REPOS_FILE, db=self.db)
            MockRM.return_value = rm
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_repos()
        output = out.getvalue()
        self.assertIn("alpha", output)
        self.assertIn("bravo", output)


class TestAddRepoCommand(CommandTestBase):

    def test_add_new_repo(self):
        with open(self.TEST_REPOS_FILE, "w") as f:
            json.dump({"repositories": []}, f)

        from commands.add_repo import add_repo
        from core.repository_manager import RepositoryManager

        rm = RepositoryManager(repos_file=self.TEST_REPOS_FILE, db=self.db)

        with patch("commands.add_repo.RepositoryManager") as MockRM:
            MockRM.return_value = rm
            with patch("sys.stdout", new_callable=StringIO) as out:
                add_repo("new-proj")
        output = out.getvalue()
        self.assertIn("added successfully", output)
        repos = rm.load_repositories()
        self.assertIn("new-proj", repos)

    def test_add_invalid_repo_name(self):
        from commands.add_repo import add_repo

        with patch("sys.stdout", new_callable=StringIO) as out:
            add_repo("bad name!")
        output = out.getvalue()
        self.assertIn("Invalid repository name", output)


class TestMigrateIssuesCommand(CommandTestBase):

    def test_migrate_imports_to_db(self):
        from commands.migrate_issues import migrate_issues

        with patch("commands.migrate_issues.FileManager") as MockFM, \
             patch("commands.migrate_issues.Database") as MockDB:
            MockFM.return_value = self.fm
            # Use a real DB via context manager mock
            MockDB.return_value.__enter__ = lambda s: self.db
            MockDB.return_value.__exit__ = lambda s, *a: None
            with patch("sys.stdout", new_callable=StringIO) as out:
                migrate_issues()
        output = out.getvalue()
        self.assertIn("Migrated", output)
        self.assertIn("1", output)


if __name__ == "__main__":
    unittest.main()
