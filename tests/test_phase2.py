"""Tests for Phase 2 — state engine, assignments, execution records, reviews,
activity log, attachments, task hierarchy, and session continuity."""

import os
import unittest

from core.database import (
    add_repository,
    block_work_item,
    create_assignment,
    create_attachment,
    create_db_and_tables,
    create_execution_record,
    create_review,
    create_work_item,
    get_activity_log,
    get_assignments,
    get_attachments,
    get_child_progress,
    get_children,
    get_current_assignment,
    get_execution_records,
    get_reviews,
    get_work_item,
    list_items_by_executor,
    transition_work_item,
    unblock_work_item,
    update_work_item,
)
from core.state_engine import (
    InvalidTransitionError,
    RepoConcurrencyError,
    TRANSITIONS,
    check_repo_concurrency,
    validate_transition,
)
from models import (
    ActivityAction,
    ExecutionStatus,
    ExecutorType,
    Priority,
    ReviewDecision,
    WorkItemState,
)


class TestStateEngine(unittest.TestCase):
    """Tests for transition validation and concurrency guard."""

    # --- Transition validation ---

    def test_valid_transitions(self):
        """Every entry in TRANSITIONS should pass validation."""
        for from_state, to_states in TRANSITIONS.items():
            for to_state in to_states:
                validate_transition(from_state, to_state)  # should not raise

    def test_invalid_transition_raises(self):
        with self.assertRaises(InvalidTransitionError):
            validate_transition(WorkItemState.queued, WorkItemState.executing)

    def test_closed_has_no_outbound_transitions(self):
        self.assertEqual(TRANSITIONS[WorkItemState.closed], set())
        for target in WorkItemState:
            if target != WorkItemState.closed:
                with self.assertRaises(InvalidTransitionError):
                    validate_transition(WorkItemState.closed, target)

    def test_rework_loops_back_to_executing(self):
        validate_transition(WorkItemState.rework_required, WorkItemState.executing)

    def test_every_state_can_reach_closed(self):
        for state in WorkItemState:
            if state == WorkItemState.closed:
                continue
            self.assertIn(WorkItemState.closed, TRANSITIONS[state])

    def test_invalid_transition_error_message(self):
        try:
            validate_transition(WorkItemState.queued, WorkItemState.accepted)
        except InvalidTransitionError as e:
            self.assertIn("queued", str(e))
            self.assertIn("accepted", str(e))


class TestStateTransitionsDB(unittest.TestCase):
    """Integration tests for transition_work_item and concurrency guard."""

    TEST_DB = "test_phase2_state.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_transition_happy_path(self):
        item = create_work_item(self.engine, "Test item")
        item = transition_work_item(self.engine, item.task_id, WorkItemState.assigned, actor="human")
        self.assertEqual(item.state, WorkItemState.assigned)

    def test_transition_full_lifecycle(self):
        """Walk an item through the entire happy path."""
        item = create_work_item(self.engine, "Full lifecycle")
        states = [
            WorkItemState.assigned,
            WorkItemState.executing,
            WorkItemState.completed,
            WorkItemState.awaiting_review,
            WorkItemState.accepted,
            WorkItemState.closed,
        ]
        for s in states:
            item = transition_work_item(self.engine, item.task_id, s)
        self.assertEqual(item.state, WorkItemState.closed)

    def test_transition_invalid_raises(self):
        item = create_work_item(self.engine, "Test item")
        with self.assertRaises(InvalidTransitionError):
            transition_work_item(self.engine, item.task_id, WorkItemState.completed)

    def test_transition_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            transition_work_item(self.engine, 9999, WorkItemState.assigned)

    def test_transition_logs_activity(self):
        item = create_work_item(self.engine, "Logged transition")
        transition_work_item(self.engine, item.task_id, WorkItemState.assigned)
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.state_change, actions)

    def test_repo_concurrency_guard(self):
        repo = add_repository(self.engine, "guarded-repo")
        item1 = create_work_item(self.engine, "Item 1", repo_name="guarded-repo")
        item2 = create_work_item(self.engine, "Item 2", repo_name="guarded-repo")
        # Move item1 to executing
        transition_work_item(self.engine, item1.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item1.task_id, WorkItemState.executing)
        # item2 should be blocked from executing
        transition_work_item(self.engine, item2.task_id, WorkItemState.assigned)
        with self.assertRaises(RepoConcurrencyError):
            transition_work_item(self.engine, item2.task_id, WorkItemState.executing)

    def test_concurrency_guard_allows_different_repos(self):
        add_repository(self.engine, "repo-a")
        add_repository(self.engine, "repo-b")
        item_a = create_work_item(self.engine, "In A", repo_name="repo-a")
        item_b = create_work_item(self.engine, "In B", repo_name="repo-b")
        for item in (item_a, item_b):
            transition_work_item(self.engine, item.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item_a.task_id, WorkItemState.executing)
        # Different repo — should succeed
        transition_work_item(self.engine, item_b.task_id, WorkItemState.executing)

    def test_concurrency_guard_no_repo(self):
        """Items without a repo should bypass concurrency guard."""
        item = create_work_item(self.engine, "No repo")
        transition_work_item(self.engine, item.task_id, WorkItemState.assigned)
        transition_work_item(self.engine, item.task_id, WorkItemState.executing)  # should not raise

    def test_rework_loop(self):
        item = create_work_item(self.engine, "Rework test")
        for s in [WorkItemState.assigned, WorkItemState.executing,
                   WorkItemState.completed, WorkItemState.awaiting_review,
                   WorkItemState.rework_required, WorkItemState.executing]:
            item = transition_work_item(self.engine, item.task_id, s)
        self.assertEqual(item.state, WorkItemState.executing)


class TestBlockMechanism(unittest.TestCase):
    TEST_DB = "test_phase2_block.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_block_and_unblock(self):
        item = create_work_item(self.engine, "Blockable")
        blocked = block_work_item(self.engine, item.task_id, "waiting on API key")
        self.assertTrue(blocked.is_blocked)
        self.assertEqual(blocked.blocked_reason, "waiting on API key")

        unblocked = unblock_work_item(self.engine, item.task_id)
        self.assertFalse(unblocked.is_blocked)
        self.assertIsNone(unblocked.blocked_reason)

    def test_block_preserves_state(self):
        item = create_work_item(self.engine, "State preserved")
        transition_work_item(self.engine, item.task_id, WorkItemState.assigned)
        blocked = block_work_item(self.engine, item.task_id, "reason")
        refreshed = get_work_item(self.engine, item.task_id)
        self.assertEqual(refreshed.state, WorkItemState.assigned)
        self.assertTrue(refreshed.is_blocked)

    def test_block_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            block_work_item(self.engine, 9999, "reason")

    def test_unblock_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            unblock_work_item(self.engine, 9999)

    def test_block_logs_activity(self):
        item = create_work_item(self.engine, "Log block")
        block_work_item(self.engine, item.task_id, "test reason", actor="tester")
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.blocked, actions)

    def test_unblock_logs_activity(self):
        item = create_work_item(self.engine, "Log unblock")
        block_work_item(self.engine, item.task_id, "test")
        unblock_work_item(self.engine, item.task_id, actor="tester")
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.unblocked, actions)


class TestAssignments(unittest.TestCase):
    TEST_DB = "test_phase2_assign.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_create_and_get_assignment(self):
        item = create_work_item(self.engine, "Assignable")
        assignment = create_assignment(self.engine, item.task_id, "alice", ExecutorType.human)
        self.assertEqual(assignment.executor, "alice")
        self.assertEqual(assignment.executor_type, ExecutorType.human)

        assignments = get_assignments(self.engine, item.task_id)
        self.assertEqual(len(assignments), 1)

    def test_assignment_history_append_only(self):
        item = create_work_item(self.engine, "Reassigned")
        create_assignment(self.engine, item.task_id, "alice", ExecutorType.human)
        create_assignment(self.engine, item.task_id, "bob", ExecutorType.agent)
        assignments = get_assignments(self.engine, item.task_id)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0].executor, "alice")
        self.assertEqual(assignments[1].executor, "bob")

    def test_get_current_assignment(self):
        item = create_work_item(self.engine, "Current")
        create_assignment(self.engine, item.task_id, "alice", ExecutorType.human)
        create_assignment(self.engine, item.task_id, "bob", ExecutorType.agent)
        current = get_current_assignment(self.engine, item.task_id)
        self.assertEqual(current.executor, "bob")

    def test_list_items_by_executor(self):
        add_repository(self.engine, "repo")
        item1 = create_work_item(self.engine, "Alice's item", repo_name="repo")
        item2 = create_work_item(self.engine, "Bob's item", repo_name="repo")
        create_assignment(self.engine, item1.task_id, "alice", ExecutorType.human)
        create_assignment(self.engine, item2.task_id, "bob", ExecutorType.agent)

        alice_items = list_items_by_executor(self.engine, "alice")
        self.assertEqual(len(alice_items), 1)
        self.assertEqual(alice_items[0].task_id, item1.task_id)

    def test_reassignment_changes_current(self):
        item = create_work_item(self.engine, "Reassign")
        create_assignment(self.engine, item.task_id, "alice", ExecutorType.human)
        create_assignment(self.engine, item.task_id, "bob", ExecutorType.human)
        # alice should no longer own it
        alice_items = list_items_by_executor(self.engine, "alice")
        self.assertEqual(len(alice_items), 0)
        bob_items = list_items_by_executor(self.engine, "bob")
        self.assertEqual(len(bob_items), 1)

    def test_assignment_logs_activity(self):
        item = create_work_item(self.engine, "Log assign")
        create_assignment(self.engine, item.task_id, "alice", ExecutorType.human, actor="admin")
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.assigned, actions)


class TestExecutionRecords(unittest.TestCase):
    TEST_DB = "test_phase2_exec.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_create_and_get_record(self):
        item = create_work_item(self.engine, "Executed")
        record = create_execution_record(
            self.engine, item.task_id, "agent-1", ExecutionStatus.success,
            branch="main", commit="abc123",
        )
        self.assertEqual(record.executor, "agent-1")
        self.assertEqual(record.status, ExecutionStatus.success)
        self.assertEqual(record.branch, "main")

    def test_multiple_attempts(self):
        item = create_work_item(self.engine, "Retried")
        create_execution_record(self.engine, item.task_id, "agent-1", ExecutionStatus.failed)
        create_execution_record(self.engine, item.task_id, "agent-1", ExecutionStatus.success)
        records = get_execution_records(self.engine, item.task_id)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].status, ExecutionStatus.failed)
        self.assertEqual(records[1].status, ExecutionStatus.success)

    def test_execution_logs_activity(self):
        item = create_work_item(self.engine, "Log exec")
        create_execution_record(self.engine, item.task_id, "agent-1", ExecutionStatus.success)
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.execution_logged, actions)


class TestReviews(unittest.TestCase):
    TEST_DB = "test_phase2_review.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_create_and_get_review(self):
        item = create_work_item(self.engine, "Reviewed")
        review = create_review(self.engine, item.task_id, "reviewer-1", ReviewDecision.accepted, note="LGTM")
        self.assertEqual(review.reviewer, "reviewer-1")
        self.assertEqual(review.decision, ReviewDecision.accepted)
        self.assertEqual(review.note, "LGTM")

    def test_review_history(self):
        item = create_work_item(self.engine, "Multi-review")
        create_review(self.engine, item.task_id, "alice", ReviewDecision.rework_required, note="fix tests")
        create_review(self.engine, item.task_id, "bob", ReviewDecision.accepted)
        reviews = get_reviews(self.engine, item.task_id)
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0].decision, ReviewDecision.rework_required)
        self.assertEqual(reviews[1].decision, ReviewDecision.accepted)

    def test_review_logs_activity(self):
        item = create_work_item(self.engine, "Log review")
        create_review(self.engine, item.task_id, "reviewer", ReviewDecision.accepted, actor="reviewer")
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.review_submitted, actions)


class TestAttachments(unittest.TestCase):
    TEST_DB = "test_phase2_attach.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_create_and_get_attachment(self):
        item = create_work_item(self.engine, "With attachment")
        att = create_attachment(self.engine, item.task_id, "/tmp/log.txt", label="Build log")
        self.assertEqual(att.url_or_path, "/tmp/log.txt")
        self.assertEqual(att.label, "Build log")

    def test_multiple_attachments(self):
        item = create_work_item(self.engine, "Multi-attach")
        create_attachment(self.engine, item.task_id, "/tmp/a.txt")
        create_attachment(self.engine, item.task_id, "/tmp/b.txt")
        atts = get_attachments(self.engine, item.task_id)
        self.assertEqual(len(atts), 2)

    def test_attachment_without_label(self):
        item = create_work_item(self.engine, "No label")
        att = create_attachment(self.engine, item.task_id, "/tmp/file.txt")
        self.assertIsNone(att.label)


class TestTaskHierarchy(unittest.TestCase):
    TEST_DB = "test_phase2_hierarchy.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_get_children(self):
        parent = create_work_item(self.engine, "Parent")
        create_work_item(self.engine, "Child 1", parent_id=parent.task_id)
        create_work_item(self.engine, "Child 2", parent_id=parent.task_id)
        children = get_children(self.engine, parent.task_id)
        self.assertEqual(len(children), 2)

    def test_child_progress_none(self):
        parent = create_work_item(self.engine, "Empty parent")
        done, total = get_child_progress(self.engine, parent.task_id)
        self.assertEqual(done, 0)
        self.assertEqual(total, 0)

    def test_child_progress_partial(self):
        parent = create_work_item(self.engine, "Parent")
        c1 = create_work_item(self.engine, "Done child", parent_id=parent.task_id)
        c2 = create_work_item(self.engine, "Open child", parent_id=parent.task_id)
        # Move c1 to accepted (counts as done)
        for s in [WorkItemState.assigned, WorkItemState.executing,
                   WorkItemState.completed, WorkItemState.awaiting_review,
                   WorkItemState.accepted]:
            transition_work_item(self.engine, c1.task_id, s)
        done, total = get_child_progress(self.engine, parent.task_id)
        self.assertEqual(done, 1)
        self.assertEqual(total, 2)

    def test_child_progress_closed_counts_as_done(self):
        parent = create_work_item(self.engine, "Parent")
        c1 = create_work_item(self.engine, "Closed child", parent_id=parent.task_id)
        transition_work_item(self.engine, c1.task_id, WorkItemState.closed)
        done, total = get_child_progress(self.engine, parent.task_id)
        self.assertEqual(done, 1)
        self.assertEqual(total, 1)


class TestActivityLog(unittest.TestCase):
    TEST_DB = "test_phase2_activity.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_create_work_item_logs_created(self):
        item = create_work_item(self.engine, "Log test")
        log = get_activity_log(self.engine, task_id=item.task_id)
        actions = [e.action for e in log]
        self.assertIn(ActivityAction.created, actions)

    def test_activity_log_limit(self):
        item = create_work_item(self.engine, "Many actions")
        for _ in range(5):
            block_work_item(self.engine, item.task_id, "reason")
            unblock_work_item(self.engine, item.task_id)
        # created + 5*(block + unblock) = 11
        all_log = get_activity_log(self.engine, task_id=item.task_id, limit=100)
        self.assertEqual(len(all_log), 11)
        limited = get_activity_log(self.engine, task_id=item.task_id, limit=3)
        self.assertEqual(len(limited), 3)

    def test_activity_log_records_actor(self):
        item = create_work_item(self.engine, "Actor test", created_by="creator")
        log = get_activity_log(self.engine, task_id=item.task_id)
        created_entry = [e for e in log if e.action == ActivityAction.created][0]
        self.assertEqual(created_entry.actor, "creator")

    def test_global_activity_log(self):
        create_work_item(self.engine, "Item A")
        create_work_item(self.engine, "Item B")
        log = get_activity_log(self.engine)
        self.assertGreaterEqual(len(log), 2)


if __name__ == "__main__":
    unittest.main()
