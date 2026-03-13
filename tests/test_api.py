"""Tests for the Phase 3 REST API."""

import os
import unittest

from fastapi.testclient import TestClient


class TestAPI(unittest.TestCase):
    """Full CRUD API tests using FastAPI TestClient."""

    TEST_DB = "test_api.db"

    def setUp(self):
        self._cleanup()
        # Point the API at a test database and disable auth
        os.environ["FORGEOPS_DB_PATH"] = self.TEST_DB
        os.environ.pop("API_BEARER_TOKEN", None)
        # Reimport to pick up env changes
        import importlib
        import config
        importlib.reload(config)
        import core.database
        importlib.reload(core.database)
        import api as api_mod
        importlib.reload(api_mod)
        self.app = api_mod.app
        self.client = TestClient(self.app)

    def tearDown(self):
        self._cleanup()
        os.environ.pop("FORGEOPS_DB_PATH", None)

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    # --- Repositories ---------------------------------------------------------

    def test_create_repository(self):
        resp = self.client.post("/repositories", json={"name": "test-repo", "org": "myorg"})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["name"], "test-repo")
        self.assertEqual(data["org"], "myorg")

    def test_list_repositories(self):
        self.client.post("/repositories", json={"name": "repo-a"})
        self.client.post("/repositories", json={"name": "repo-b"})
        resp = self.client.get("/repositories")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_get_repository(self):
        self.client.post("/repositories", json={"name": "my-repo"})
        resp = self.client.get("/repositories/my-repo")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "my-repo")

    def test_get_repository_not_found(self):
        resp = self.client.get("/repositories/ghost")
        self.assertEqual(resp.status_code, 404)

    def test_update_repository(self):
        self.client.post("/repositories", json={"name": "updatable"})
        resp = self.client.patch("/repositories/updatable", json={"org": "new-org"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["org"], "new-org")

    def test_delete_repository(self):
        self.client.post("/repositories", json={"name": "doomed"})
        resp = self.client.delete("/repositories/doomed")
        self.assertEqual(resp.status_code, 204)
        resp = self.client.get("/repositories/doomed")
        self.assertEqual(resp.status_code, 404)

    # --- Work Items -----------------------------------------------------------

    def test_create_work_item(self):
        resp = self.client.post("/work-items", json={"title": "Test item"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Test item")
        self.assertEqual(resp.json()["state"], "queued")

    def test_list_work_items(self):
        self.client.post("/work-items", json={"title": "A"})
        self.client.post("/work-items", json={"title": "B"})
        resp = self.client.get("/work-items")
        self.assertEqual(len(resp.json()), 2)

    def test_list_work_items_filter_state(self):
        self.client.post("/work-items", json={"title": "Queued"})
        self.client.post("/work-items", json={"title": "Closed", "state": "closed"})
        resp = self.client.get("/work-items", params={"state": "queued"})
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["title"], "Queued")

    def test_get_work_item(self):
        create_resp = self.client.post("/work-items", json={"title": "Fetch me"})
        task_id = create_resp.json()["task_id"]
        resp = self.client.get(f"/work-items/{task_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Fetch me")

    def test_get_work_item_not_found(self):
        resp = self.client.get("/work-items/9999")
        self.assertEqual(resp.status_code, 404)

    def test_update_work_item(self):
        create_resp = self.client.post("/work-items", json={"title": "Original"})
        task_id = create_resp.json()["task_id"]
        resp = self.client.patch(f"/work-items/{task_id}", json={"title": "Updated"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Updated")

    def test_transition_work_item(self):
        create_resp = self.client.post("/work-items", json={"title": "Transition me"})
        task_id = create_resp.json()["task_id"]
        resp = self.client.post(f"/work-items/{task_id}/transition", json={"state": "assigned"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["state"], "assigned")

    def test_transition_invalid(self):
        create_resp = self.client.post("/work-items", json={"title": "Bad transition"})
        task_id = create_resp.json()["task_id"]
        resp = self.client.post(f"/work-items/{task_id}/transition", json={"state": "accepted"})
        self.assertEqual(resp.status_code, 409)

    def test_block_and_unblock(self):
        create_resp = self.client.post("/work-items", json={"title": "Blockable"})
        task_id = create_resp.json()["task_id"]
        resp = self.client.post(f"/work-items/{task_id}/block", json={"reason": "waiting"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_blocked"])

        resp = self.client.post(f"/work-items/{task_id}/unblock")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_blocked"])

    def test_children_endpoint(self):
        parent = self.client.post("/work-items", json={"title": "Parent"}).json()
        self.client.post("/work-items", json={"title": "Child", "parent_id": parent["task_id"]})
        resp = self.client.get(f"/work-items/{parent['task_id']}/children")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["children"]), 1)
        self.assertEqual(resp.json()["progress"]["total"], 1)

    # --- Assignments ----------------------------------------------------------

    def test_create_and_list_assignments(self):
        item = self.client.post("/work-items", json={"title": "Assigned"}).json()
        resp = self.client.post(
            f"/work-items/{item['task_id']}/assignments",
            json={"executor": "alice", "executor_type": "human"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["executor"], "alice")

        resp = self.client.get(f"/work-items/{item['task_id']}/assignments")
        self.assertEqual(len(resp.json()), 1)

    def test_current_assignment(self):
        item = self.client.post("/work-items", json={"title": "Current"}).json()
        self.client.post(f"/work-items/{item['task_id']}/assignments", json={"executor": "alice"})
        self.client.post(f"/work-items/{item['task_id']}/assignments", json={"executor": "bob"})
        resp = self.client.get(f"/work-items/{item['task_id']}/assignments/current")
        self.assertEqual(resp.json()["executor"], "bob")

    def test_executor_work_items(self):
        item = self.client.post("/work-items", json={"title": "Alice's"}).json()
        self.client.post(f"/work-items/{item['task_id']}/assignments", json={"executor": "alice"})
        resp = self.client.get("/executors/alice/work-items")
        self.assertEqual(len(resp.json()), 1)

    # --- Execution Records ----------------------------------------------------

    def test_create_and_list_runs(self):
        item = self.client.post("/work-items", json={"title": "Run me"}).json()
        resp = self.client.post(
            f"/work-items/{item['task_id']}/runs",
            json={"executor": "agent-1", "status": "success", "branch": "main"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "success")

        resp = self.client.get(f"/work-items/{item['task_id']}/runs")
        self.assertEqual(len(resp.json()), 1)

    # --- Reviews --------------------------------------------------------------

    def test_create_and_list_reviews(self):
        item = self.client.post("/work-items", json={"title": "Reviewed"}).json()
        resp = self.client.post(
            f"/work-items/{item['task_id']}/reviews",
            json={"reviewer": "alice", "decision": "accepted", "note": "LGTM"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["decision"], "accepted")

        resp = self.client.get(f"/work-items/{item['task_id']}/reviews")
        self.assertEqual(len(resp.json()), 1)

    # --- Attachments ----------------------------------------------------------

    def test_create_and_list_attachments(self):
        item = self.client.post("/work-items", json={"title": "Attached"}).json()
        resp = self.client.post(
            f"/work-items/{item['task_id']}/attachments",
            json={"url_or_path": "/tmp/log.txt", "label": "Build log"},
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.client.get(f"/work-items/{item['task_id']}/attachments")
        self.assertEqual(len(resp.json()), 1)

    # --- Activity & Status ----------------------------------------------------

    def test_activity_log(self):
        self.client.post("/work-items", json={"title": "Logged"})
        resp = self.client.get("/activity")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_status_overview(self):
        self.client.post("/work-items", json={"title": "Status test"})
        resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 1)

    # --- Legacy endpoint ------------------------------------------------------

    def test_legacy_issues_endpoint(self):
        self.client.post("/work-items", json={"title": "Legacy"})
        resp = self.client.get("/issues")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)


class TestAPIAuth(unittest.TestCase):
    """Auth tests — verify bearer token enforcement."""

    TEST_DB = "test_api_auth.db"

    def setUp(self):
        self._cleanup()
        os.environ["FORGEOPS_DB_PATH"] = self.TEST_DB
        os.environ["API_BEARER_TOKEN"] = "test-secret-token"
        import importlib
        import config
        importlib.reload(config)
        import core.database
        importlib.reload(core.database)
        import api as api_mod
        importlib.reload(api_mod)
        self.app = api_mod.app
        self.client = TestClient(self.app)

    def tearDown(self):
        self._cleanup()
        os.environ.pop("FORGEOPS_DB_PATH", None)
        os.environ.pop("API_BEARER_TOKEN", None)

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_missing_token_returns_401(self):
        resp = self.client.get("/work-items")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_token_returns_401(self):
        resp = self.client.get("/work-items", headers={"Authorization": "Bearer wrong"})
        self.assertEqual(resp.status_code, 401)

    def test_correct_token_succeeds(self):
        resp = self.client.get("/work-items", headers={"Authorization": "Bearer test-secret-token"})
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
