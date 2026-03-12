import json
import os
import shutil
import unittest

from core.file_manager import FileManager


class TestFileManager(unittest.TestCase):

    TEST_ISSUES_DIR = "test_issues"
    TEST_COUNTER_FILE = "test_issue_counter.txt"

    def setUp(self):
        # Clean slate for each test
        for path in (self.TEST_ISSUES_DIR, self.TEST_COUNTER_FILE):
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
        self.fm = FileManager(
            issues_dir=self.TEST_ISSUES_DIR,
            counter_file=self.TEST_COUNTER_FILE,
        )

    def tearDown(self):
        if os.path.isdir(self.TEST_ISSUES_DIR):
            shutil.rmtree(self.TEST_ISSUES_DIR)
        if os.path.isfile(self.TEST_COUNTER_FILE):
            os.remove(self.TEST_COUNTER_FILE)

    # --- get_next_issue_id ---

    def test_first_issue_id_is_001(self):
        self.assertEqual(self.fm.get_next_issue_id(), "ISSUE-001")

    def test_issue_ids_increment(self):
        self.fm.get_next_issue_id()
        self.assertEqual(self.fm.get_next_issue_id(), "ISSUE-002")
        self.assertEqual(self.fm.get_next_issue_id(), "ISSUE-003")

    def test_counter_persists_across_instances(self):
        self.fm.get_next_issue_id()  # 1
        fm2 = FileManager(
            issues_dir=self.TEST_ISSUES_DIR,
            counter_file=self.TEST_COUNTER_FILE,
        )
        self.assertEqual(fm2.get_next_issue_id(), "ISSUE-002")

    def test_counter_file_written(self):
        self.fm.get_next_issue_id()
        with open(self.TEST_COUNTER_FILE) as f:
            self.assertEqual(f.read().strip(), "1")

    # --- save_issue / load_issue round-trip ---

    def _make_issue(self, issue_id="ISSUE-001"):
        return {
            "id": issue_id,
            "title": "Test issue",
            "description": "A description",
            "repository": "test-repo",
            "created_at": "2026-01-01T00:00:00Z",
        }

    def test_save_and_load_issue(self):
        issue = self._make_issue()
        self.fm.save_issue(issue)
        loaded = self.fm.load_issue("ISSUE-001")
        self.assertEqual(loaded, issue)

    def test_save_creates_json_file(self):
        issue = self._make_issue()
        path = self.fm.save_issue(issue)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            self.assertEqual(json.load(f), issue)

    def test_load_nonexistent_returns_none(self):
        self.assertIsNone(self.fm.load_issue("ISSUE-999"))

    # --- load_all_issues ---

    def test_load_all_issues_empty(self):
        self.assertEqual(self.fm.load_all_issues(), [])

    def test_load_all_issues_sorted(self):
        # Save in reverse order to verify sorting
        for num in (3, 1, 2):
            self.fm.save_issue(self._make_issue(f"ISSUE-{num:03d}"))
        issues = self.fm.load_all_issues()
        ids = [i["id"] for i in issues]
        self.assertEqual(ids, ["ISSUE-001", "ISSUE-002", "ISSUE-003"])

    def test_load_all_issues_ignores_non_issue_files(self):
        # Create a file that doesn't match the ISSUE-*.json pattern
        other_file = os.path.join(self.TEST_ISSUES_DIR, "notes.json")
        with open(other_file, "w") as f:
            json.dump({"some": "data"}, f)
        self.fm.save_issue(self._make_issue())
        issues = self.fm.load_all_issues()
        self.assertEqual(len(issues), 1)

    def test_issues_dir_created_on_init(self):
        self.assertTrue(os.path.isdir(self.TEST_ISSUES_DIR))


if __name__ == "__main__":
    unittest.main()
