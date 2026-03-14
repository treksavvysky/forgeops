"""API error path tests — 404s, 409s, 400s, concurrency guard via API."""

import os
import unittest
import importlib

from fastapi.testclient import TestClient


class TestAPIErrors(unittest.TestCase):
    TEST_DB = "test_api_errors.db"

    def setUp(self):
        self._cleanup()
        os.environ["FORGEOPS_DB_PATH"] = self.TEST_DB
        os.environ.pop("API_BEARER_TOKEN", None)
        import config
        importlib.reload(config)
        import core.database
        importlib.reload(core.database)
        import api as api_mod
        importlib.reload(api_mod)
        self.client = TestClient(api_mod.app)

    def tearDown(self):
        self._cleanup()
        os.environ.pop("FORGEOPS_DB_PATH", None)

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def _create_item(self, title="Test", **kwargs):
        return self.client.post("/work-items", json={"title": title, **kwargs}).json()

    # --- Work item errors ---

    def test_update_nonexistent_work_item(self):
        resp = self.client.patch("/work-items/9999", json={"title": "x"})
        self.assertEqual(resp.status_code, 404)

    def test_update_empty_body(self):
        item = self._create_item()
        resp = self.client.patch(f"/work-items/{item['task_id']}", json={})
        self.assertEqual(resp.status_code, 400)

    def test_transition_nonexistent(self):
        resp = self.client.post("/work-items/9999/transition", json={"state": "assigned"})
        self.assertEqual(resp.status_code, 404)

    def test_block_nonexistent(self):
        resp = self.client.post("/work-items/9999/block", json={"reason": "x"})
        self.assertEqual(resp.status_code, 404)

    def test_unblock_nonexistent(self):
        resp = self.client.post("/work-items/9999/unblock")
        self.assertEqual(resp.status_code, 404)

    # --- Concurrency guard via API ---

    def test_concurrency_guard_via_api(self):
        self.client.post("/repositories", json={"name": "guarded"})
        item1 = self._create_item("Item 1", repo_name="guarded")
        item2 = self._create_item("Item 2", repo_name="guarded")

        # Walk item1 to executing
        self.client.post(f"/work-items/{item1['task_id']}/transition", json={"state": "assigned"})
        self.client.post(f"/work-items/{item1['task_id']}/transition", json={"state": "executing"})

        # item2 should be blocked
        self.client.post(f"/work-items/{item2['task_id']}/transition", json={"state": "assigned"})
        resp = self.client.post(f"/work-items/{item2['task_id']}/transition", json={"state": "executing"})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("already has an item", resp.json()["detail"])

    # --- Nested resource 404s ---

    def test_assignment_on_nonexistent_item(self):
        resp = self.client.post("/work-items/9999/assignments", json={"executor": "alice"})
        self.assertEqual(resp.status_code, 404)

    def test_current_assignment_none(self):
        item = self._create_item()
        resp = self.client.get(f"/work-items/{item['task_id']}/assignments/current")
        self.assertEqual(resp.status_code, 404)

    def test_run_on_nonexistent_item(self):
        resp = self.client.post(
            "/work-items/9999/runs",
            json={"executor": "agent", "status": "success"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_review_on_nonexistent_item(self):
        resp = self.client.post(
            "/work-items/9999/reviews",
            json={"reviewer": "alice", "decision": "accepted"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_attachment_on_nonexistent_item(self):
        resp = self.client.post(
            "/work-items/9999/attachments",
            json={"url_or_path": "/tmp/x"},
        )
        self.assertEqual(resp.status_code, 404)

    # --- Repository errors ---

    def test_update_nonexistent_repo(self):
        resp = self.client.patch("/repositories/ghost", json={"org": "x"})
        self.assertEqual(resp.status_code, 404)

    def test_update_repo_empty_body(self):
        self.client.post("/repositories", json={"name": "repo"})
        resp = self.client.patch("/repositories/repo", json={})
        self.assertEqual(resp.status_code, 400)

    def test_delete_nonexistent_repo(self):
        resp = self.client.delete("/repositories/ghost")
        self.assertEqual(resp.status_code, 404)

    # --- Empty list responses ---

    def test_empty_runs(self):
        item = self._create_item()
        resp = self.client.get(f"/work-items/{item['task_id']}/runs")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_empty_reviews(self):
        item = self._create_item()
        resp = self.client.get(f"/work-items/{item['task_id']}/reviews")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_empty_attachments(self):
        item = self._create_item()
        resp = self.client.get(f"/work-items/{item['task_id']}/attachments")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_executor_no_items(self):
        resp = self.client.get("/executors/nobody/work-items")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # --- Full lifecycle via API ---

    def test_full_lifecycle_via_api(self):
        """Walk an item through the full lifecycle via the API."""
        self.client.post("/repositories", json={"name": "lifecycle-repo"})
        item = self._create_item("Lifecycle", repo_name="lifecycle-repo")
        tid = item["task_id"]

        states = ["assigned", "executing", "completed", "awaiting_review", "accepted", "closed"]
        for state in states:
            resp = self.client.post(f"/work-items/{tid}/transition", json={"state": state})
            self.assertEqual(resp.status_code, 200, f"Failed on transition to {state}")
            self.assertEqual(resp.json()["state"], state)


if __name__ == "__main__":
    unittest.main()
