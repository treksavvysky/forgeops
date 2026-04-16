"""Tests for the Phase 3 event hook system."""

import os
import unittest

from core.database import (
    block_work_item,
    create_assignment,
    create_db_and_tables,
    create_review,
    create_work_item,
    transition_work_item,
    unblock_work_item,
)
from core.hooks import HookEvent, HookRegistry, hooks
from core.state_engine import RepoConcurrencyError
from core.database import add_repository
from models import ExecutorType, ReviewDecision, WorkItemState


class TestHookRegistry(unittest.TestCase):
    """Unit tests for the HookRegistry class."""

    def setUp(self):
        self.registry = HookRegistry()

    def test_subscribe_and_fire(self):
        received = []
        self.registry.subscribe(HookEvent.on_state_change, lambda p: received.append(p))
        self.registry.fire(HookEvent.on_state_change, {"task_id": 1})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["task_id"], 1)

    def test_decorator_registration(self):
        received = []

        @self.registry.on(HookEvent.on_blocked)
        def handler(payload):
            received.append(payload)

        self.registry.fire(HookEvent.on_blocked, {"reason": "test"})
        self.assertEqual(len(received), 1)

    def test_unsubscribe(self):
        received = []

        def handler(p):
            received.append(p)

        self.registry.subscribe(HookEvent.on_state_change, handler)
        self.registry.unsubscribe(HookEvent.on_state_change, handler)
        self.registry.fire(HookEvent.on_state_change, {"task_id": 1})
        self.assertEqual(len(received), 0)

    def test_unsubscribe_nonexistent(self):
        # Should not raise
        self.registry.unsubscribe(HookEvent.on_state_change, lambda p: None)

    def test_multiple_handlers(self):
        results = []
        self.registry.subscribe(HookEvent.on_assigned, lambda p: results.append("a"))
        self.registry.subscribe(HookEvent.on_assigned, lambda p: results.append("b"))
        self.registry.fire(HookEvent.on_assigned, {})
        self.assertEqual(results, ["a", "b"])

    def test_failing_handler_does_not_block_others(self):
        results = []

        def bad_handler(p):
            raise RuntimeError("boom")

        self.registry.subscribe(HookEvent.on_state_change, bad_handler)
        self.registry.subscribe(HookEvent.on_state_change, lambda p: results.append("ok"))
        self.registry.fire(HookEvent.on_state_change, {})
        self.assertEqual(results, ["ok"])

    def test_clear_all(self):
        self.registry.subscribe(HookEvent.on_state_change, lambda p: None)
        self.registry.subscribe(HookEvent.on_blocked, lambda p: None)
        self.registry.clear()
        self.assertEqual(len(self.registry._handlers), 0)

    def test_clear_specific_event(self):
        self.registry.subscribe(HookEvent.on_state_change, lambda p: None)
        self.registry.subscribe(HookEvent.on_blocked, lambda p: None)
        self.registry.clear(HookEvent.on_state_change)
        self.assertNotIn(HookEvent.on_state_change, self.registry._handlers)
        self.assertIn(HookEvent.on_blocked, self.registry._handlers)

    def test_fire_unsubscribed_event(self):
        # Should not raise
        self.registry.fire(HookEvent.on_rework, {"task_id": 1})


class TestHooksIntegration(unittest.TestCase):
    """Integration tests — hooks fire from database operations."""

    TEST_DB = "test_hooks.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)
        self.received = []
        hooks.clear()

    def tearDown(self):
        hooks.clear()
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_state_change_hook_fires(self):
        hooks.subscribe(HookEvent.on_state_change, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Hook test")
        transition_work_item(self.engine, item.task_id, WorkItemState.assigned)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["old_state"], "queued")
        self.assertEqual(self.received[0]["new_state"], "assigned")

    def test_execution_complete_hook_fires(self):
        hooks.subscribe(HookEvent.on_execution_complete, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Complete test")
        transition_work_item(self.engine, item.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item.task_id, WorkItemState.executing)
        transition_work_item(self.engine, item.task_id, WorkItemState.completed)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["task_id"], item.task_id)

    def test_rework_hook_fires(self):
        hooks.subscribe(HookEvent.on_rework, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Rework test")
        for s in [
            WorkItemState.assigned,
            WorkItemState.executing,
            WorkItemState.completed,
            WorkItemState.awaiting_review,
            WorkItemState.rework_required,
        ]:
            transition_work_item(self.engine, item.task_id, s)
        self.assertEqual(len(self.received), 1)

    def test_blocked_hook_fires(self):
        hooks.subscribe(HookEvent.on_blocked, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Block hook")
        block_work_item(self.engine, item.task_id, "reason")
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["reason"], "reason")

    def test_unblocked_hook_fires(self):
        hooks.subscribe(HookEvent.on_unblocked, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Unblock hook")
        block_work_item(self.engine, item.task_id, "reason")
        unblock_work_item(self.engine, item.task_id)
        self.assertEqual(len(self.received), 1)

    def test_assigned_hook_fires(self):
        hooks.subscribe(HookEvent.on_assigned, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Assign hook")
        create_assignment(self.engine, item.task_id, "alice", ExecutorType.human)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["executor"], "alice")

    def test_review_submitted_hook_fires(self):
        hooks.subscribe(HookEvent.on_review_submitted, lambda p: self.received.append(p))
        item = create_work_item(self.engine, "Review hook")
        create_review(self.engine, item.task_id, "bob", ReviewDecision.accepted)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["decision"], "accepted")

    def test_repo_conflict_hook_fires(self):
        hooks.subscribe(HookEvent.on_repo_conflict, lambda p: self.received.append(p))
        add_repository(self.engine, "conflict-repo")
        item1 = create_work_item(self.engine, "Item 1", repo_name="conflict-repo")
        item2 = create_work_item(self.engine, "Item 2", repo_name="conflict-repo")
        transition_work_item(self.engine, item1.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item1.task_id, WorkItemState.executing)
        transition_work_item(self.engine, item2.task_id, WorkItemState.assigned)
        with self.assertRaises(RepoConcurrencyError):
            transition_work_item(self.engine, item2.task_id, WorkItemState.executing)
        self.assertEqual(len(self.received), 1)


if __name__ == "__main__":
    unittest.main()
