import json
import os
import uuid
from datetime import datetime

class TaskManager:
    def __init__(self, task_list_name, created_by, association):
        self.task_list_name = task_list_name
        self.file_path = os.path.join("task_lists", f"{task_list_name}.json")
        self.task_data = None

        # Ensure task_lists directory exists
        os.makedirs("task_lists", exist_ok=True)

        if os.path.exists(self.file_path):
            self._load_task_list()
        else:
            self.task_data = {
                "version": "1.0.0",
                "name": task_list_name,
                "association": association,
                "created_by": created_by,
                "created_on": datetime.utcnow().isoformat(),
                "tasks": []
            }
            self._save_task_list()

    def _save_task_list(self):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.task_data, f, indent=4)
        except IOError as e:
            print(f"Error saving task list: {e}")

    def _load_task_list(self):
        try:
            with open(self.file_path, 'r') as f:
                self.task_data = json.load(f)
        except IOError as e:
            print(f"Error loading task list: {e}")
            # Inform constructor to create a new one (handled by the initial check)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from task list: {e}")
            # Potentially handle corrupted file by creating a new list or raising error
            self.task_data = None # Or some default structure

    def add_task(self, subject, description, priority, status="open"):
        new_task = {
            "task_id": str(uuid.uuid4()),
            "subject": subject,
            "description": description,
            "status": status,
            "date_created": datetime.utcnow().isoformat(),
            "priority": priority,
            "comments": []
        }
        self.task_data["tasks"].append(new_task)
        self._save_task_list()
        return new_task

    def add_comment_to_task(self, task_id, comment_text):
        for task in self.task_data["tasks"]:
            if task["task_id"] == task_id:
                comment = {
                    "comment": comment_text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                task["comments"].append(comment)
                self._save_task_list()
                return True
        return False

    def get_task_by_id(self, task_id):
        for task in self.task_data["tasks"]:
            if task["task_id"] == task_id:
                return task
        return None

    def update_task(self, task_id, **kwargs):
        task = self.get_task_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if key in task:
                    task[key] = value
            self._save_task_list()
            return True
        return False

    def delete_task(self, task_id):
        initial_len = len(self.task_data["tasks"])
        self.task_data["tasks"] = [task for task in self.task_data["tasks"] if task["task_id"] != task_id]
        if len(self.task_data["tasks"]) < initial_len:
            self._save_task_list()
            return True
        return False
