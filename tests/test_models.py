"""Tests for Pydantic/SQLModel models."""

import unittest

from models import (
    Assignment,
    ExecutionRecord,
    ExecutionStatus,
    ExecutorType,
    Priority,
    RepoStatus,
    Repository,
    Review,
    ReviewDecision,
    WorkItem,
    WorkItemState,
)


class TestEnums(unittest.TestCase):

    def test_repo_status_values(self):
        self.assertEqual(RepoStatus.active.value, "active")
        self.assertEqual(RepoStatus.archived.value, "archived")

    def test_work_item_states(self):
        expected = {"queued", "assigned", "executing", "completed",
                    "awaiting_review", "accepted", "rework_required", "closed"}
        self.assertEqual({s.value for s in WorkItemState}, expected)

    def test_priority_levels(self):
        expected = {"low", "medium", "high", "urgent"}
        self.assertEqual({p.value for p in Priority}, expected)

    def test_executor_types(self):
        self.assertEqual(ExecutorType.human.value, "human")
        self.assertEqual(ExecutorType.agent.value, "agent")

    def test_execution_status_values(self):
        expected = {"success", "failed", "partial"}
        self.assertEqual({s.value for s in ExecutionStatus}, expected)

    def test_review_decisions(self):
        expected = {"accepted", "rework_required"}
        self.assertEqual({d.value for d in ReviewDecision}, expected)


class TestModelDefaults(unittest.TestCase):

    def test_repository_defaults(self):
        r = Repository(name="test")
        self.assertEqual(r.status, RepoStatus.active)
        self.assertIsNone(r.org)
        self.assertIsNone(r.default_branch)
        self.assertIsNone(r.url)
        self.assertIsNone(r.description)

    def test_work_item_defaults(self):
        w = WorkItem(title="test")
        self.assertEqual(w.state, WorkItemState.queued)
        self.assertEqual(w.priority, Priority.medium)
        self.assertFalse(w.is_blocked)
        self.assertIsNone(w.blocked_reason)
        self.assertIsNone(w.parent_id)
        self.assertIsNotNone(w.created_at)
        self.assertIsNotNone(w.updated_at)

    def test_assignment_fields(self):
        a = Assignment(task_id=1, executor="agent-1", executor_type=ExecutorType.agent)
        self.assertEqual(a.executor, "agent-1")
        self.assertEqual(a.executor_type, ExecutorType.agent)
        self.assertIsNotNone(a.assigned_at)

    def test_execution_record_fields(self):
        e = ExecutionRecord(task_id=1, executor="agent-1", status=ExecutionStatus.success)
        self.assertEqual(e.status, ExecutionStatus.success)
        self.assertIsNone(e.branch)
        self.assertIsNone(e.commit)

    def test_review_fields(self):
        r = Review(task_id=1, reviewer="human-1", decision=ReviewDecision.accepted)
        self.assertEqual(r.decision, ReviewDecision.accepted)
        self.assertIsNone(r.note)


if __name__ == "__main__":
    unittest.main()
