"""Tests for the ForgeOps MCP server tools."""

import json
import os
import unittest

# Override DB path before any imports touch the engine
os.environ["FORGEOPS_DB_PATH"] = "test_mcp.db"

import importlib
import config
importlib.reload(config)

from mcp_server import (
    _get_engine,
    forgeops_list_work_items,
    forgeops_get_work_item,
    forgeops_create_work_item,
    forgeops_update_work_item,
    forgeops_transition,
    forgeops_block,
    forgeops_unblock,
    forgeops_assign,
    forgeops_my_items,
    forgeops_log_run,
    forgeops_list_runs,
    forgeops_submit_review,
    forgeops_list_reviews,
    forgeops_attach,
    forgeops_list_repos,
    forgeops_add_repo,
    forgeops_status,
    forgeops_activity,
    forgeops_children,
)
import mcp_server


def _parse(result: str) -> dict:
    return json.loads(result)


class TestMCPTools(unittest.TestCase):
    TEST_DB = "test_mcp.db"

    def setUp(self):
        self._cleanup()
        # Reset the cached engine
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

    def test_create_and_get_work_item(self):
        result = _parse(forgeops_create_work_item("Test item"))
        self.assertTrue(result["success"])
        task_id = result["item"]["task_id"]

        result = _parse(forgeops_get_work_item(task_id))
        self.assertTrue(result["success"])
        self.assertEqual(result["item"]["title"], "Test item")

    def test_list_work_items(self):
        forgeops_create_work_item("A")
        forgeops_create_work_item("B")
        result = _parse(forgeops_list_work_items())
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    def test_list_work_items_filter_state(self):
        forgeops_create_work_item("Queued")
        result = _parse(forgeops_list_work_items(state="queued"))
        self.assertEqual(result["count"], 1)

    def test_update_work_item(self):
        r = _parse(forgeops_create_work_item("Original"))
        task_id = r["item"]["task_id"]
        r = _parse(forgeops_update_work_item(task_id, title="Updated"))
        self.assertTrue(r["success"])
        self.assertEqual(r["item"]["title"], "Updated")

    def test_get_nonexistent(self):
        result = _parse(forgeops_get_work_item(9999))
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "NOT_FOUND")

    def test_transition(self):
        r = _parse(forgeops_create_work_item("Transition"))
        task_id = r["item"]["task_id"]
        r = _parse(forgeops_transition(task_id, "assigned"))
        self.assertTrue(r["success"])
        self.assertEqual(r["item"]["state"], "assigned")

    def test_invalid_transition(self):
        r = _parse(forgeops_create_work_item("Bad"))
        task_id = r["item"]["task_id"]
        r = _parse(forgeops_transition(task_id, "accepted"))
        self.assertFalse(r["success"])

    def test_block_and_unblock(self):
        r = _parse(forgeops_create_work_item("Blockable"))
        task_id = r["item"]["task_id"]

        r = _parse(forgeops_block(task_id, "waiting"))
        self.assertTrue(r["success"])
        self.assertTrue(r["item"]["is_blocked"])

        r = _parse(forgeops_unblock(task_id))
        self.assertTrue(r["success"])
        self.assertFalse(r["item"]["is_blocked"])

    def test_assign_and_my_items(self):
        r = _parse(forgeops_create_work_item("Assignable"))
        task_id = r["item"]["task_id"]

        r = _parse(forgeops_assign(task_id, "alice", "human"))
        self.assertTrue(r["success"])
        self.assertEqual(r["assignment"]["executor"], "alice")

        r = _parse(forgeops_my_items("alice"))
        self.assertTrue(r["success"])
        self.assertEqual(r["count"], 1)

    def test_log_run_and_list(self):
        r = _parse(forgeops_create_work_item("Runnable"))
        task_id = r["item"]["task_id"]

        r = _parse(forgeops_log_run(task_id, "agent-1", "success", branch="main"))
        self.assertTrue(r["success"])
        self.assertEqual(r["run"]["status"], "success")

        r = _parse(forgeops_list_runs(task_id))
        self.assertTrue(r["success"])
        self.assertEqual(len(r["runs"]), 1)

    def test_review_and_list(self):
        r = _parse(forgeops_create_work_item("Reviewable"))
        task_id = r["item"]["task_id"]

        r = _parse(forgeops_submit_review(task_id, "bob", "accepted", note="LGTM"))
        self.assertTrue(r["success"])
        self.assertEqual(r["review"]["decision"], "accepted")

        r = _parse(forgeops_list_reviews(task_id))
        self.assertTrue(r["success"])
        self.assertEqual(len(r["reviews"]), 1)

    def test_attach(self):
        r = _parse(forgeops_create_work_item("Attached"))
        task_id = r["item"]["task_id"]

        r = _parse(forgeops_attach(task_id, "/tmp/log.txt", label="Build log"))
        self.assertTrue(r["success"])

    def test_repos(self):
        r = _parse(forgeops_add_repo("test-repo", org="myorg"))
        self.assertTrue(r["success"])

        r = _parse(forgeops_list_repos())
        self.assertTrue(r["success"])
        self.assertEqual(len(r["repositories"]), 1)

    def test_status(self):
        forgeops_create_work_item("Status test")
        r = _parse(forgeops_status())
        self.assertTrue(r["success"])
        self.assertEqual(r["total"], 1)

    def test_activity(self):
        forgeops_create_work_item("Activity test")
        r = _parse(forgeops_activity())
        self.assertTrue(r["success"])
        self.assertGreaterEqual(len(r["entries"]), 1)

    def test_children(self):
        parent = _parse(forgeops_create_work_item("Parent"))
        parent_id = parent["item"]["task_id"]
        forgeops_create_work_item("Child", parent_id=parent_id)

        r = _parse(forgeops_children(parent_id))
        self.assertTrue(r["success"])
        self.assertEqual(len(r["children"]), 1)
        self.assertEqual(r["progress"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
