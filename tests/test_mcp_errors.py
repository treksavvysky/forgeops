"""MCP tool error path tests — invalid enums, missing items, edge cases."""

import json
import os
import unittest
import importlib

os.environ["FORGEOPS_DB_PATH"] = "test_mcp_errors.db"
import config
importlib.reload(config)

import mcp_server
from mcp_server import (
    forgeops_assign,
    forgeops_block,
    forgeops_create_work_item,
    forgeops_list_work_items,
    forgeops_log_run,
    forgeops_submit_review,
    forgeops_transition,
    forgeops_unblock,
    forgeops_update_work_item,
    forgeops_attach,
    forgeops_get_work_item,
)


def _parse(result: str) -> dict:
    return json.loads(result)


class TestMCPErrors(unittest.TestCase):
    TEST_DB = "test_mcp_errors.db"

    def setUp(self):
        self._cleanup()
        mcp_server._engine = None
        os.environ["FORGEOPS_DB_PATH"] = self.TEST_DB
        importlib.reload(config)
        import core.database
        importlib.reload(core.database)

    def tearDown(self):
        if mcp_server._engine:
            mcp_server._engine.dispose()
        mcp_server._engine = None
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def _create(self, title="Test"):
        return _parse(forgeops_create_work_item(title))["item"]["task_id"]

    # --- Invalid enum values ---

    def test_invalid_state_in_transition(self):
        tid = self._create()
        r = _parse(forgeops_transition(tid, "bogus_state"))
        self.assertFalse(r["success"])

    def test_invalid_priority_in_create(self):
        r = _parse(forgeops_create_work_item("Bad priority", priority="critical"))
        self.assertFalse(r["success"])
        self.assertEqual(r["error"]["code"], "VALIDATION_ERROR")

    def test_invalid_executor_type(self):
        tid = self._create()
        r = _parse(forgeops_assign(tid, "alice", "robot"))
        self.assertFalse(r["success"])

    def test_invalid_execution_status(self):
        tid = self._create()
        r = _parse(forgeops_log_run(tid, "agent", "completed"))
        self.assertFalse(r["success"])

    def test_invalid_review_decision(self):
        tid = self._create()
        r = _parse(forgeops_submit_review(tid, "bob", "maybe"))
        self.assertFalse(r["success"])

    # --- Not found ---

    def test_transition_nonexistent(self):
        r = _parse(forgeops_transition(9999, "assigned"))
        self.assertFalse(r["success"])
        self.assertEqual(r["error"]["code"], "NOT_FOUND")

    def test_block_nonexistent(self):
        r = _parse(forgeops_block(9999, "reason"))
        self.assertFalse(r["success"])

    def test_unblock_nonexistent(self):
        r = _parse(forgeops_unblock(9999))
        self.assertFalse(r["success"])

    def test_assign_nonexistent(self):
        r = _parse(forgeops_assign(9999, "alice"))
        self.assertFalse(r["success"])

    def test_log_run_nonexistent(self):
        r = _parse(forgeops_log_run(9999, "agent", "success"))
        self.assertFalse(r["success"])

    def test_review_nonexistent(self):
        r = _parse(forgeops_submit_review(9999, "bob", "accepted"))
        self.assertFalse(r["success"])

    def test_attach_nonexistent(self):
        r = _parse(forgeops_attach(9999, "/tmp/x"))
        self.assertFalse(r["success"])

    # --- Edge cases ---

    def test_update_no_fields(self):
        tid = self._create()
        r = _parse(forgeops_update_work_item(tid))
        self.assertFalse(r["success"])
        self.assertEqual(r["error"]["code"], "VALIDATION_ERROR")

    def test_update_nonexistent(self):
        r = _parse(forgeops_update_work_item(9999, title="x"))
        self.assertFalse(r["success"])

    def test_list_with_invalid_state_filter(self):
        r = _parse(forgeops_list_work_items(state="bogus"))
        self.assertFalse(r["success"])

    def test_invalid_priority_filter(self):
        r = _parse(forgeops_list_work_items(priority="extreme"))
        self.assertFalse(r["success"])

    def test_concurrency_guard_via_mcp(self):
        from mcp_server import forgeops_add_repo
        forgeops_add_repo("guard-repo")
        tid1 = _parse(forgeops_create_work_item("Item 1", repo_name="guard-repo"))["item"]["task_id"]
        tid2 = _parse(forgeops_create_work_item("Item 2", repo_name="guard-repo"))["item"]["task_id"]

        forgeops_transition(tid1, "assigned")
        forgeops_transition(tid1, "executing")
        forgeops_transition(tid2, "assigned")
        r = _parse(forgeops_transition(tid2, "executing"))
        self.assertFalse(r["success"])
        self.assertIn("REPOCONCURRENCYERROR", r["error"]["code"])


if __name__ == "__main__":
    unittest.main()
