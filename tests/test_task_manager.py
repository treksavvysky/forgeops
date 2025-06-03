import unittest
import os
import json
import shutil
import uuid
from datetime_truncate import truncate
from datetime import datetime, timezone

# Adjust the path to import TaskManager from the core directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.task_manager import TaskManager

class TestTaskManager(unittest.TestCase):

    TEST_TASK_LISTS_DIR = "task_lists"
    TEST_USER = "test_user"
    TEST_ASSOCIATION = "test_project"

    def setUp(self):
        # Ensure the test task lists directory exists and is empty
        if os.path.exists(self.TEST_TASK_LISTS_DIR):
            shutil.rmtree(self.TEST_TASK_LISTS_DIR)
        os.makedirs(self.TEST_TASK_LISTS_DIR, exist_ok=True)

    def tearDown(self):
        # Clean up the test task lists directory
        if os.path.exists(self.TEST_TASK_LISTS_DIR):
            shutil.rmtree(self.TEST_TASK_LISTS_DIR)

    def _generate_unique_list_name(self):
        return f"test_list_{uuid.uuid4()}"

    def test_create_new_task_list(self):
        list_name = self._generate_unique_list_name()
        tm = TaskManager(list_name, self.TEST_USER, self.TEST_ASSOCIATION)
        
        file_path = os.path.join(self.TEST_TASK_LISTS_DIR, f"{list_name}.json")
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        self.assertEqual(data['version'], "1.0.0")
        self.assertEqual(data['name'], list_name)
        self.assertEqual(data['association'], self.TEST_ASSOCIATION)
        self.assertEqual(data['created_by'], self.TEST_USER)
        self.assertTrue('created_on' in data)
        self.assertEqual(data['tasks'], [])
        self.assertIsNotNone(tm.task_data)

    def test_load_existing_task_list(self):
        list_name = self._generate_unique_list_name()
        file_path = os.path.join(self.TEST_TASK_LISTS_DIR, f"{list_name}.json")
        
        dummy_data = {
            "version": "1.0.0",
            "name": list_name,
            "association": "dummy_association",
            "created_by": "dummy_user",
            "created_on": datetime.utcnow().isoformat(),
            "tasks": [{"task_id": "dummy_id", "subject": "Dummy Task"}]
        }
        with open(file_path, 'w') as f:
            json.dump(dummy_data, f)
            
        tm = TaskManager(list_name, "another_user", "another_association") # These should be ignored
        
        self.assertIsNotNone(tm.task_data)
        self.assertEqual(tm.task_data['name'], list_name)
        self.assertEqual(tm.task_data['association'], "dummy_association")
        self.assertEqual(tm.task_data['created_by'], "dummy_user")
        self.assertEqual(len(tm.task_data['tasks']), 1)
        self.assertEqual(tm.task_data['tasks'][0]['subject'], "Dummy Task")

    def test_add_task(self):
        list_name = self._generate_unique_list_name()
        tm = TaskManager(list_name, self.TEST_USER, self.TEST_ASSOCIATION)
        
        subject = "New Test Task"
        description = "A description for the test task."
        priority = "high"
        
        # Store current time before adding task, truncated to seconds for comparison
        time_before_add = truncate(datetime.utcnow().replace(tzinfo=timezone.utc), 'second')

        new_task = tm.add_task(subject, description, priority, status="pending")
        
        self.assertEqual(len(tm.task_data['tasks']), 1)
        task_in_data = tm.task_data['tasks'][0]
        
        self.assertEqual(task_in_data['subject'], subject)
        self.assertEqual(task_in_data['description'], description)
        self.assertEqual(task_in_data['priority'], priority)
        self.assertEqual(task_in_data['status'], "pending")
        self.assertTrue('task_id' in task_in_data)
        self.assertIsNotNone(task_in_data['task_id'])
        self.assertEqual(task_in_data['comments'], [])
        
        # Compare dates (ignoring microseconds for robustness)
        task_created_at = truncate(datetime.fromisoformat(task_in_data['date_created'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc), 'second')
        self.assertGreaterEqual(task_created_at, time_before_add)

        # Check if file is updated
        file_path = os.path.join(self.TEST_TASK_LISTS_DIR, f"{list_name}.json")
        with open(file_path, 'r') as f:
            data_from_file = json.load(f)
        self.assertEqual(len(data_from_file['tasks']), 1)
        self.assertEqual(data_from_file['tasks'][0]['subject'], subject)

    def test_add_comment_to_task(self):
        list_name = self._generate_unique_list_name()
        tm = TaskManager(list_name, self.TEST_USER, self.TEST_ASSOCIATION)
        
        task = tm.add_task("Task for Commenting", "Desc", "medium")
        task_id = task['task_id']
        
        comment_text = "This is a test comment."

        # Store current time before adding comment, truncated to seconds for comparison
        time_before_comment = truncate(datetime.utcnow().replace(tzinfo=timezone.utc), 'second')
        
        result = tm.add_comment_to_task(task_id, comment_text)
        self.assertTrue(result)
        
        self.assertEqual(len(tm.task_data['tasks'][0]['comments']), 1)
        comment_in_data = tm.task_data['tasks'][0]['comments'][0]
        
        self.assertEqual(comment_in_data['comment'], comment_text)
        self.assertTrue('timestamp' in comment_in_data)

        comment_timestamp = truncate(datetime.fromisoformat(comment_in_data['timestamp'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc), 'second')
        self.assertGreaterEqual(comment_timestamp, time_before_comment)

        # Check if file is updated
        file_path = os.path.join(self.TEST_TASK_LISTS_DIR, f"{list_name}.json")
        with open(file_path, 'r') as f:
            data_from_file = json.load(f)
        self.assertEqual(len(data_from_file['tasks'][0]['comments']), 1)
        self.assertEqual(data_from_file['tasks'][0]['comments'][0]['comment'], comment_text)

    def test_add_comment_to_non_existent_task(self):
        list_name = self._generate_unique_list_name()
        tm = TaskManager(list_name, self.TEST_USER, self.TEST_ASSOCIATION)
        result = tm.add_comment_to_task("non-existent-id", "A comment")
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
