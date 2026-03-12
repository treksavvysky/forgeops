import json
import os
import unittest

from core.db import Database
from core.repository_manager import RepositoryManager


class TestRepositoryManager(unittest.TestCase):

    TEST_REPOS_FILE = "test_repos.json"
    TEST_DB_PATH = "test_repos.db"

    def setUp(self):
        self._cleanup()
        self.db = Database(db_path=self.TEST_DB_PATH)
        self.rm = RepositoryManager(repos_file=self.TEST_REPOS_FILE, db=self.db)

    def tearDown(self):
        self.db.close()
        self._cleanup()

    def _cleanup(self):
        for path in (self.TEST_REPOS_FILE, self.TEST_DB_PATH):
            if os.path.isfile(path):
                os.remove(path)

    # --- validate_repo_name ---

    def test_valid_names(self):
        for name in ("my-repo", "repo_1", "AB", "a" * 50):
            valid, _ = self.rm.validate_repo_name(name)
            self.assertTrue(valid, f"{name!r} should be valid")

    def test_invalid_chars(self):
        valid, msg = self.rm.validate_repo_name("bad repo!")
        self.assertFalse(valid)
        self.assertIn("letters", msg)

    def test_too_short(self):
        valid, msg = self.rm.validate_repo_name("x")
        self.assertFalse(valid)
        self.assertIn("2 characters", msg)

    def test_too_long(self):
        valid, msg = self.rm.validate_repo_name("a" * 51)
        self.assertFalse(valid)
        self.assertIn("50 characters", msg)

    # --- suggest_repositories ---

    def test_exact_match_case_insensitive(self):
        found, suggestions = self.rm.suggest_repositories("Jules-Dev-Kit")
        self.assertTrue(found)
        self.assertEqual(suggestions, [])

    def test_partial_match_returns_suggestions(self):
        found, suggestions = self.rm.suggest_repositories("jules")
        self.assertFalse(found)
        self.assertIn("jules-dev-kit", suggestions)

    def test_no_match_returns_empty(self):
        found, suggestions = self.rm.suggest_repositories("zzz-nonexistent")
        self.assertFalse(found)
        self.assertEqual(suggestions, [])

    # --- add_repository ---

    def test_add_new_repository(self):
        result = self.rm.add_repository("new-repo")
        self.assertTrue(result)
        repos = self.rm.load_repositories()
        self.assertIn("new-repo", repos)

    def test_add_duplicate_returns_false(self):
        self.rm.add_repository("dupe-repo")
        result = self.rm.add_repository("dupe-repo")
        self.assertFalse(result)

    def test_add_repository_keeps_sorted(self):
        self.rm.add_repository("zzz-last")
        self.rm.add_repository("aaa-first")
        repos = self.rm.load_repositories()
        self.assertEqual(repos, sorted(repos))

    def test_add_repository_syncs_to_db(self):
        self.rm.add_repository("db-synced")
        db_repos = self.db.get_repositories()
        self.assertIn("db-synced", db_repos)

    # --- _init_repos_registry ---

    def test_default_repos_created(self):
        repos = self.rm.load_repositories()
        self.assertIn("jules-dev-kit", repos)
        self.assertTrue(len(repos) >= 5)

    def test_existing_registry_not_overwritten(self):
        # Write a custom registry, then create a new RepositoryManager
        with open(self.TEST_REPOS_FILE, "w") as f:
            json.dump({"repositories": ["custom-repo"]}, f)
        rm2 = RepositoryManager(repos_file=self.TEST_REPOS_FILE, db=self.db)
        repos = rm2.load_repositories()
        self.assertEqual(repos, ["custom-repo"])


if __name__ == "__main__":
    unittest.main()
