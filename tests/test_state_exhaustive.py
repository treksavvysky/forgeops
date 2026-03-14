"""Exhaustive state engine tests — every invalid transition pair must raise."""

import os
import unittest

from core.database import (
    add_repository,
    create_db_and_tables,
    create_work_item,
    transition_work_item,
)
from core.state_engine import (
    InvalidTransitionError,
    RepoConcurrencyError,
    TRANSITIONS,
    validate_transition,
)
from models import WorkItemState


class TestExhaustiveTransitions(unittest.TestCase):
    """Test every (from, to) state pair: valid ones pass, invalid ones raise."""

    def test_all_invalid_transitions_raise(self):
        all_states = list(WorkItemState)
        for from_state in all_states:
            allowed = TRANSITIONS[from_state]
            for to_state in all_states:
                if to_state in allowed:
                    continue
                if from_state == to_state:
                    continue
                with self.assertRaises(
                    InvalidTransitionError,
                    msg=f"{from_state.value} → {to_state.value} should be invalid",
                ):
                    validate_transition(from_state, to_state)

    def test_self_transitions_are_invalid(self):
        """No state can transition to itself."""
        for state in WorkItemState:
            with self.assertRaises(InvalidTransitionError):
                validate_transition(state, state)

    def test_transition_count(self):
        """Verify the total number of valid transitions."""
        total = sum(len(targets) for targets in TRANSITIONS.values())
        # queued(2) + assigned(3) + executing(3) + completed(2) +
        # awaiting_review(3) + accepted(1) + rework_required(2) + closed(0) = 16
        self.assertEqual(total, 16)


class TestConcurrencyGuardEdgeCases(unittest.TestCase):
    TEST_DB = "test_concurrency_edge.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_guard_clears_after_item_leaves_executing(self):
        """After item1 leaves executing, item2 can enter."""
        add_repository(self.engine, "repo")
        item1 = create_work_item(self.engine, "Item 1", repo_name="repo")
        item2 = create_work_item(self.engine, "Item 2", repo_name="repo")

        transition_work_item(self.engine, item1.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item1.task_id, WorkItemState.executing)
        # item1 completes
        transition_work_item(self.engine, item1.task_id, WorkItemState.completed)
        # Now item2 should be able to execute
        transition_work_item(self.engine, item2.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item2.task_id, WorkItemState.executing)

    def test_guard_clears_after_item_closed(self):
        add_repository(self.engine, "repo")
        item1 = create_work_item(self.engine, "Item 1", repo_name="repo")
        item2 = create_work_item(self.engine, "Item 2", repo_name="repo")

        transition_work_item(self.engine, item1.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item1.task_id, WorkItemState.executing)
        transition_work_item(self.engine, item1.task_id, WorkItemState.closed)

        transition_work_item(self.engine, item2.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item2.task_id, WorkItemState.executing)  # should work

    def test_guard_error_message_contains_repo_name(self):
        add_repository(self.engine, "my-repo")
        item1 = create_work_item(self.engine, "Item 1", repo_name="my-repo")
        item2 = create_work_item(self.engine, "Item 2", repo_name="my-repo")

        transition_work_item(self.engine, item1.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item1.task_id, WorkItemState.executing)
        transition_work_item(self.engine, item2.task_id, WorkItemState.assigned)

        try:
            transition_work_item(self.engine, item2.task_id, WorkItemState.executing)
            self.fail("Should have raised RepoConcurrencyError")
        except RepoConcurrencyError as e:
            self.assertIn("my-repo", str(e))
            self.assertIn(str(item1.task_id), str(e))

    def test_three_items_same_repo(self):
        """Third item also blocked while first is executing."""
        add_repository(self.engine, "repo")
        items = [create_work_item(self.engine, f"Item {i}", repo_name="repo") for i in range(3)]
        for item in items:
            transition_work_item(self.engine, item.task_id, WorkItemState.assigned)

        transition_work_item(self.engine, items[0].task_id, WorkItemState.executing)

        for item in items[1:]:
            with self.assertRaises(RepoConcurrencyError):
                transition_work_item(self.engine, item.task_id, WorkItemState.executing)


if __name__ == "__main__":
    unittest.main()
