"""Integration tests for Phase 2 CLI commands — state, assign, execution, review,
session, attachments, tasks."""

import json
import os
import unittest
from io import StringIO
from unittest.mock import patch

from core.database import (
    add_repository,
    create_db_and_tables,
    create_work_item,
    create_assignment,
    create_execution_record,
    transition_work_item,
    block_work_item,
)
from models import ExecutionStatus, ExecutorType, WorkItemState


class Phase2CommandBase(unittest.TestCase):
    TEST_DB = "test_cmd_phase2.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)
        self.patcher = patch("core.database.DB_PATH", self.TEST_DB)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)


# --- State commands -------------------------------------------------------

class TestUpdateStatusCommand(Phase2CommandBase):

    def test_valid_transition(self):
        item = create_work_item(self.engine, "Transition me")
        from commands.state import update_status
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                update_status(item.task_id, "assigned")
        self.assertIn("assigned", out.getvalue())

    def test_invalid_state_string(self):
        item = create_work_item(self.engine, "Bad state")
        from commands.state import update_status
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                update_status(item.task_id, "nonexistent")
        self.assertIn("Unknown state", out.getvalue())

    def test_invalid_transition(self):
        item = create_work_item(self.engine, "Invalid")
        from commands.state import update_status
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                update_status(item.task_id, "accepted")
        self.assertIn("Invalid transition", out.getvalue())

    def test_nonexistent_item(self):
        from commands.state import update_status
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                update_status(9999, "assigned")
        self.assertIn("not found", out.getvalue())


class TestBlockCommand(Phase2CommandBase):

    def test_block(self):
        item = create_work_item(self.engine, "Block me")
        from commands.state import block
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                block(item.task_id, "waiting on key")
        self.assertIn("blocked", out.getvalue())

    def test_block_nonexistent(self):
        from commands.state import block
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                block(9999, "reason")
        self.assertIn("not found", out.getvalue())

    def test_unblock(self):
        item = create_work_item(self.engine, "Unblock me")
        block_work_item(self.engine, item.task_id, "reason")
        from commands.state import unblock
        with patch("commands.state.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                unblock(item.task_id)
        self.assertIn("unblocked", out.getvalue())


# --- Assign commands ------------------------------------------------------

class TestAssignCommand(Phase2CommandBase):

    def test_assign(self):
        item = create_work_item(self.engine, "Assign me")
        from commands.assign import assign
        with patch("commands.assign.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                assign(item.task_id, "alice", "human")
        self.assertIn("assigned to alice", out.getvalue())

    def test_assign_invalid_type(self):
        item = create_work_item(self.engine, "Bad type")
        from commands.assign import assign
        with patch("commands.assign.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                assign(item.task_id, "alice", "robot")
        self.assertIn("Invalid executor type", out.getvalue())

    def test_assign_nonexistent(self):
        from commands.assign import assign
        with patch("commands.assign.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                assign(9999, "alice", "human")
        self.assertIn("not found", out.getvalue())

    def test_my_issues_empty(self):
        from commands.assign import my_issues
        with patch("commands.assign.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                my_issues("nobody")
        self.assertIn("No work items", out.getvalue())

    def test_my_issues_with_items(self):
        item = create_work_item(self.engine, "Alice's item")
        create_assignment(self.engine, item.task_id, "alice", ExecutorType.human)
        from commands.assign import my_issues
        with patch("commands.assign.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                my_issues("alice")
        self.assertIn("Alice's item", out.getvalue())


# --- Execution commands ---------------------------------------------------

class TestLogRunCommand(Phase2CommandBase):

    def test_log_run(self):
        item = create_work_item(self.engine, "Run me")
        from commands.execution import log_run
        with patch("commands.execution.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                log_run(item.task_id, "agent-1", "success", branch="main",
                        commit="abc123", auto_detect_git=False)
        self.assertIn("logged", out.getvalue())

    def test_log_run_invalid_status(self):
        item = create_work_item(self.engine, "Bad status")
        from commands.execution import log_run
        with patch("commands.execution.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                log_run(item.task_id, "agent-1", "unknown", auto_detect_git=False)
        self.assertIn("Invalid status", out.getvalue())

    def test_log_run_nonexistent(self):
        from commands.execution import log_run
        with patch("commands.execution.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                log_run(9999, "agent-1", "success", auto_detect_git=False)
        self.assertIn("not found", out.getvalue())

    def test_runs_empty(self):
        item = create_work_item(self.engine, "No runs")
        from commands.execution import runs
        with patch("commands.execution.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                runs(item.task_id)
        self.assertIn("No execution records", out.getvalue())

    def test_runs_with_records(self):
        item = create_work_item(self.engine, "Has runs")
        create_execution_record(self.engine, item.task_id, "agent-1",
                                ExecutionStatus.success, branch="main")
        from commands.execution import runs
        with patch("commands.execution.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                runs(item.task_id)
        self.assertIn("agent-1", out.getvalue())
        self.assertIn("main", out.getvalue())


# --- Review commands ------------------------------------------------------

class TestReviewCommands(Phase2CommandBase):

    def _make_reviewable(self):
        item = create_work_item(self.engine, "Reviewable")
        for s in [WorkItemState.assigned, WorkItemState.executing,
                   WorkItemState.completed, WorkItemState.awaiting_review]:
            transition_work_item(self.engine, item.task_id, s)
        return item

    def test_review_queue_empty(self):
        from commands.review import review_queue
        with patch("commands.review.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                review_queue()
        self.assertIn("No items awaiting review", out.getvalue())

    def test_review_queue_with_items(self):
        self._make_reviewable()
        from commands.review import review_queue
        with patch("commands.review.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                review_queue()
        self.assertIn("Reviewable", out.getvalue())

    def test_approve(self):
        item = self._make_reviewable()
        from commands.review import approve
        with patch("commands.review.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                approve(item.task_id, "reviewer-1")
        self.assertIn("approved", out.getvalue())

    def test_approve_wrong_state(self):
        item = create_work_item(self.engine, "Not reviewable")
        from commands.review import approve
        with patch("commands.review.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                approve(item.task_id, "reviewer-1")
        self.assertIn("not 'awaiting_review'", out.getvalue())

    def test_request_changes(self):
        item = self._make_reviewable()
        from commands.review import request_changes
        with patch("commands.review.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                request_changes(item.task_id, "reviewer-1", note="fix tests")
        self.assertIn("rework", out.getvalue())
        self.assertIn("fix tests", out.getvalue())


# --- Session commands -----------------------------------------------------

class TestSessionCommands(Phase2CommandBase):

    def test_status_empty(self):
        from commands.session import status_overview
        with patch("commands.session.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                status_overview()
        self.assertIn("No work items", out.getvalue())

    def test_status_with_items(self):
        create_work_item(self.engine, "Item A")
        create_work_item(self.engine, "Item B")
        from commands.session import status_overview
        with patch("commands.session.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                status_overview()
        self.assertIn("queued", out.getvalue())

    def test_next_actions_empty(self):
        from commands.session import next_actions
        with patch("commands.session.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                next_actions()
        self.assertIn("Nothing needs human attention", out.getvalue())

    def test_next_actions_blocked_items(self):
        item = create_work_item(self.engine, "Blocked item")
        block_work_item(self.engine, item.task_id, "waiting")
        from commands.session import next_actions
        with patch("commands.session.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                next_actions()
        self.assertIn("Blocked item", out.getvalue())

    def test_snapshot_and_resume(self):
        import tempfile
        from pathlib import Path
        create_work_item(self.engine, "Snapshot me")

        snapshot_file = Path(tempfile.gettempdir()) / "test_snapshot.json"

        from commands.session import snapshot, resume
        with patch("commands.session.create_db_and_tables", return_value=self.engine), \
             patch("commands.session.SNAPSHOT_FILE", snapshot_file):
            with patch("sys.stdout", new_callable=StringIO) as out:
                snapshot()
            self.assertIn("Snapshot saved", out.getvalue())
            self.assertTrue(snapshot_file.exists())

        with patch("commands.session.SNAPSHOT_FILE", snapshot_file):
            with patch("sys.stdout", new_callable=StringIO) as out:
                resume()
            self.assertIn("Snapshot me", out.getvalue())

        snapshot_file.unlink()

    def test_resume_no_snapshot(self):
        from pathlib import Path
        from commands.session import resume
        with patch("commands.session.SNAPSHOT_FILE", Path("/tmp/nonexistent_snapshot.json")):
            with patch("sys.stdout", new_callable=StringIO) as out:
                resume()
        self.assertIn("No snapshot found", out.getvalue())


# --- Attachment commands --------------------------------------------------

class TestAttachmentCommands(Phase2CommandBase):

    def test_attach(self):
        item = create_work_item(self.engine, "Attach to me")
        from commands.attachments import attach
        with patch("commands.attachments.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                attach(item.task_id, "/tmp/file.txt", label="log")
        self.assertIn("Attachment added", out.getvalue())

    def test_attach_nonexistent(self):
        from commands.attachments import attach
        with patch("commands.attachments.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                attach(9999, "/tmp/file.txt")
        self.assertIn("not found", out.getvalue())

    def test_list_attachments_empty(self):
        item = create_work_item(self.engine, "No attachments")
        from commands.attachments import list_attachments
        with patch("commands.attachments.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_attachments(item.task_id)
        self.assertIn("No attachments", out.getvalue())


# --- Task hierarchy commands ----------------------------------------------

class TestTaskCommands(Phase2CommandBase):

    def test_add_task(self):
        parent = create_work_item(self.engine, "Parent")
        from commands.tasks import add_task
        with patch("commands.tasks.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                add_task(parent.task_id, "Sub-task")
        self.assertIn("Sub-task", out.getvalue())
        self.assertIn("created under", out.getvalue())

    def test_add_task_nonexistent_parent(self):
        from commands.tasks import add_task
        with patch("commands.tasks.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                add_task(9999, "Orphan")
        self.assertIn("not found", out.getvalue())

    def test_list_tasks_empty(self):
        parent = create_work_item(self.engine, "Empty parent")
        from commands.tasks import list_tasks
        with patch("commands.tasks.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_tasks(parent.task_id)
        self.assertIn("No sub-tasks", out.getvalue())

    def test_list_tasks_with_children(self):
        parent = create_work_item(self.engine, "Parent")
        create_work_item(self.engine, "Child A", parent_id=parent.task_id)
        create_work_item(self.engine, "Child B", parent_id=parent.task_id)
        from commands.tasks import list_tasks
        with patch("commands.tasks.create_db_and_tables", return_value=self.engine):
            with patch("sys.stdout", new_callable=StringIO) as out:
                list_tasks(parent.task_id)
        output = out.getvalue()
        self.assertIn("Child A", output)
        self.assertIn("Child B", output)
        self.assertIn("0/2", output)


if __name__ == "__main__":
    unittest.main()
