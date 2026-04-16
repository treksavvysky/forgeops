"""Tests for RepositoryManager (SQLModel-backed)."""

import os
import unittest

from core.database import add_repository, create_db_and_tables
from core.repository_manager import RepositoryManager


class TestRepositoryManager(unittest.TestCase):
    TEST_DB = "test_repo_mgr.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)
        self.rm = RepositoryManager(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

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
        add_repository(self.engine, "Jules-Dev-Kit")
        found, suggestions = self.rm.suggest_repositories("Jules-Dev-Kit")
        self.assertTrue(found)
        self.assertEqual(suggestions, [])

    def test_partial_match_returns_suggestions(self):
        add_repository(self.engine, "jules-dev-kit")
        found, suggestions = self.rm.suggest_repositories("jules")
        self.assertFalse(found)
        self.assertIn("jules-dev-kit", suggestions)

    def test_no_match_returns_empty(self):
        add_repository(self.engine, "some-repo")
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

    # --- update / remove ---

    def test_update_repository(self):
        self.rm.add_repository("updatable")
        result = self.rm.update_repository("updatable", org="new-org")
        self.assertIsNotNone(result)
        self.assertEqual(result.org, "new-org")

    def test_remove_repository(self):
        self.rm.add_repository("removable")
        self.assertTrue(self.rm.remove_repository("removable"))
        self.assertNotIn("removable", self.rm.load_repositories())

    def test_remove_nonexistent_returns_false(self):
        self.assertFalse(self.rm.remove_repository("ghost"))

    # --- get_repository ---

    def test_get_existing(self):
        self.rm.add_repository("findme")
        repo = self.rm.get_repository("findme")
        self.assertIsNotNone(repo)
        self.assertEqual(repo.name, "findme")

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.rm.get_repository("nope"))


if __name__ == "__main__":
    unittest.main()
