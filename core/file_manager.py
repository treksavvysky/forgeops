"""
File Manager - Handles file I/O operations for issues
"""

import json
from pathlib import Path


class FileManager:
    def __init__(self, issues_dir="issues", counter_file="issue_counter.txt"):
        self.issues_dir = Path(issues_dir)
        self.counter_file = Path(counter_file)
        
        # Create issues directory if it doesn't exist
        self.issues_dir.mkdir(exist_ok=True)
    
    def get_next_issue_id(self):
        """Get the next available issue ID."""
        try:
            if self.counter_file.exists():
                with open(self.counter_file, 'r') as f:
                    counter = int(f.read().strip())
            else:
                counter = 0
            
            # Increment counter
            counter += 1
            
            # Save new counter
            with open(self.counter_file, 'w') as f:
                f.write(str(counter))
            
            return f"ISSUE-{counter:03d}"
        
        except (ValueError, IOError) as e:
            raise Exception(f"Error managing issue counter: {e}")
    
    def save_issue(self, issue_data):
        """Save issue data to JSON file."""
        try:
            issue_file = self.issues_dir / f"{issue_data['id']}.json"
            with open(issue_file, 'w') as f:
                json.dump(issue_data, f, indent=2)
            return issue_file
        except IOError as e:
            raise Exception(f"Error saving issue: {e}")
    
    def load_issue(self, issue_id):
        """Load a specific issue from JSON file."""
        try:
            issue_file = self.issues_dir / f"{issue_id}.json"
            if not issue_file.exists():
                return None
            
            with open(issue_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise Exception(f"Error loading issue {issue_id}: {e}")
    
    def load_all_issues(self):
        """Load all issues from the issues directory."""
        issues = []
        
        if not self.issues_dir.exists():
            return issues
        
        try:
            for issue_file in self.issues_dir.glob("ISSUE-*.json"):
                with open(issue_file, 'r') as f:
                    issue_data = json.load(f)
                    issues.append(issue_data)
        except (json.JSONDecodeError, IOError) as e:
            raise Exception(f"Error loading issues: {e}")
        
        # Sort by issue ID for consistent ordering
        issues.sort(key=lambda x: x['id'])
        return issues
