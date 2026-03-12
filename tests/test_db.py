import os
import unittest

from core.db import Database


class TestDatabase(unittest.TestCase):

    TEST_DB_PATH = "test_forgeops.db"

    def setUp(self):
        self._cleanup()
        self.db = Database(db_path=self.TEST_DB_PATH)

    def tearDown(self):
        self.db.close()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)

    def _make_issue(self, issue_id="ISSUE-001", repo="test-repo"):
        return {
            "id": issue_id,
            "title": "Test issue",
            "description": "desc",
            "repository": repo,
            "created_at": "2026-01-01T00:00:00Z",
        }

    # --- schema ---

    def test_schema_created(self):
        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        self.assertIn("issues", tables)
        self.assertIn("repositories", tables)

    # --- repositories ---

    def test_add_and_get_repository(self):
        self.db.add_repository("my-repo")
        self.assertIn("my-repo", self.db.get_repositories())

    def test_add_duplicate_repository_ignored(self):
        self.db.add_repository("dup")
        self.db.add_repository("dup")
        repos = self.db.get_repositories()
        self.assertEqual(repos.count("dup"), 1)

    def test_repositories_sorted(self):
        for name in ("charlie", "alpha", "bravo"):
            self.db.add_repository(name)
        self.assertEqual(self.db.get_repositories(), ["alpha", "bravo", "charlie"])

    # --- issues ---

    def test_add_and_get_issue(self):
        issue = self._make_issue()
        self.db.add_issue(issue)
        issues = self.db.get_issues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], "ISSUE-001")
        self.assertEqual(issues[0]["title"], "Test issue")

    def test_get_issues_empty(self):
        self.assertEqual(self.db.get_issues(), [])

    def test_add_issue_upsert(self):
        issue = self._make_issue()
        self.db.add_issue(issue)
        issue["title"] = "Updated title"
        self.db.add_issue(issue)
        issues = self.db.get_issues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["title"], "Updated title")

    def test_issues_sorted_by_id(self):
        for num in (3, 1, 2):
            self.db.add_issue(self._make_issue(f"ISSUE-{num:03d}"))
        ids = [i["id"] for i in self.db.get_issues()]
        self.assertEqual(ids, ["ISSUE-001", "ISSUE-002", "ISSUE-003"])

    def test_issue_description_optional(self):
        issue = self._make_issue()
        issue["description"] = None
        self.db.add_issue(issue)
        loaded = self.db.get_issues()[0]
        self.assertIsNone(loaded["description"])

    # --- context manager ---

    def test_context_manager(self):
        with Database(db_path=self.TEST_DB_PATH) as db:
            db.add_repository("ctx-repo")
        # Connection should be closed but data persisted
        db2 = Database(db_path=self.TEST_DB_PATH)
        self.assertIn("ctx-repo", db2.get_repositories())
        db2.close()


if __name__ == "__main__":
    unittest.main()
