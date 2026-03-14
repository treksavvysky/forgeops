"""Property-based tests using Hypothesis — fuzz model validation."""

import os
import unittest
import string

from hypothesis import given, strategies as st, settings, assume

from core.database import create_db_and_tables, create_work_item, get_work_item
from core.repository_manager import RepositoryManager
from core.state_engine import TRANSITIONS, validate_transition, InvalidTransitionError
from models import Priority, WorkItemState, ExecutorType, ExecutionStatus, ReviewDecision


class TestEnumRoundTrip(unittest.TestCase):
    """All enum values must survive string round-trip."""

    @given(st.sampled_from(list(WorkItemState)))
    def test_work_item_state_roundtrip(self, state):
        self.assertEqual(WorkItemState(state.value), state)

    @given(st.sampled_from(list(Priority)))
    def test_priority_roundtrip(self, priority):
        self.assertEqual(Priority(priority.value), priority)

    @given(st.sampled_from(list(ExecutorType)))
    def test_executor_type_roundtrip(self, etype):
        self.assertEqual(ExecutorType(etype.value), etype)

    @given(st.sampled_from(list(ExecutionStatus)))
    def test_execution_status_roundtrip(self, status):
        self.assertEqual(ExecutionStatus(status.value), status)

    @given(st.sampled_from(list(ReviewDecision)))
    def test_review_decision_roundtrip(self, decision):
        self.assertEqual(ReviewDecision(decision.value), decision)


class TestInvalidEnumValues(unittest.TestCase):
    """Random strings that aren't valid enum values should raise."""

    @given(st.text(min_size=1, max_size=50))
    def test_random_string_not_valid_state(self, s):
        valid = {e.value for e in WorkItemState}
        assume(s not in valid)
        with self.assertRaises(ValueError):
            WorkItemState(s)

    @given(st.text(min_size=1, max_size=50))
    def test_random_string_not_valid_priority(self, s):
        valid = {e.value for e in Priority}
        assume(s not in valid)
        with self.assertRaises(ValueError):
            Priority(s)


class TestTransitionProperties(unittest.TestCase):
    """Property-based tests for the state transition graph."""

    @given(
        from_state=st.sampled_from(list(WorkItemState)),
        to_state=st.sampled_from(list(WorkItemState)),
    )
    def test_transition_either_valid_or_raises(self, from_state, to_state):
        """Every transition pair either succeeds or raises InvalidTransitionError."""
        allowed = TRANSITIONS[from_state]
        if to_state in allowed:
            validate_transition(from_state, to_state)  # should not raise
        else:
            with self.assertRaises(InvalidTransitionError):
                validate_transition(from_state, to_state)

    @given(st.sampled_from(list(WorkItemState)))
    def test_self_transition_always_invalid(self, state):
        with self.assertRaises(InvalidTransitionError):
            validate_transition(state, state)


class TestRepoNameValidation(unittest.TestCase):
    """Property-based tests for repository name validation."""

    VALID_CHARS = string.ascii_lowercase + string.digits + "-_"

    def setUp(self):
        self.rm = RepositoryManager.__new__(RepositoryManager)

    @given(st.text(alphabet=VALID_CHARS, min_size=2, max_size=100))
    def test_valid_names_accepted(self, name):
        """Names with valid chars and length should pass."""
        is_valid, _ = self.rm.validate_repo_name(name)
        self.assertTrue(is_valid, f"'{name}' should be valid")

    @given(st.text(min_size=101, max_size=200))
    def test_long_names_rejected(self, name):
        is_valid, _ = self.rm.validate_repo_name(name)
        self.assertFalse(is_valid)

    @given(st.text(max_size=1))
    def test_short_names_rejected(self, name):
        is_valid, _ = self.rm.validate_repo_name(name)
        self.assertFalse(is_valid)


class TestWorkItemCreationProperties(unittest.TestCase):
    """Property-based tests for work item creation."""

    TEST_DB = "test_property_db.db"

    def setUp(self):
        self._cleanup()
        self.engine = create_db_and_tables(self.TEST_DB)

    def tearDown(self):
        self.engine.dispose()
        self._cleanup()

    def _cleanup(self):
        if os.path.isfile(self.TEST_DB):
            os.remove(self.TEST_DB)

    @given(
        title=st.text(min_size=1, max_size=200),
        priority=st.sampled_from(list(Priority)),
    )
    @settings(max_examples=20)
    def test_created_item_has_correct_fields(self, title, priority):
        item = create_work_item(self.engine, title, priority=priority)
        self.assertEqual(item.title, title)
        self.assertEqual(item.priority, priority)
        self.assertEqual(item.state, WorkItemState.queued)
        self.assertFalse(item.is_blocked)

        fetched = get_work_item(self.engine, item.task_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, title)


if __name__ == "__main__":
    unittest.main()
