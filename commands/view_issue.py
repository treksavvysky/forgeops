"""
View Issue Command - Display detailed view of a specific issue
"""

import re

from core.file_manager import FileManager
from utils.helpers import format_datetime


def view_issue(issue_id):
    """Display detailed view of a specific issue."""
    file_manager = FileManager()
    
    # Validate issue ID format
    if not re.match(r'^ISSUE-\d{3}$', issue_id):
        print(f"Invalid issue ID format: {issue_id}")
        print("Expected format: ISSUE-XXX (e.g., ISSUE-001)")
        return
    
    try:
        issue = file_manager.load_issue(issue_id)
    except Exception as e:
        print(f"Error loading issue: {e}")
        return
    
    if not issue:
        print(f"Issue {issue_id} not found.")
        
        # Suggest similar issue IDs
        try:
            all_issues = file_manager.load_all_issues()
            if all_issues:
                print(f"\nAvailable issues:")
                for issue_item in all_issues[-5:]:  # Show last 5 issues
                    print(f"  {issue_item['id']}")
        except Exception:
            pass  # Don't let suggestion errors break the command
        return
    
    # Display detailed issue information
    print("\n" + "="*60)
    print(f"ISSUE DETAILS: {issue['id']}")
    print("="*60)
    
    print(f"Title:       {issue['title']}")
    print(f"Repository:  {issue['repository']}")
    print(f"Created:     {format_datetime(issue.get('created_at'))}")
    print(f"Description:")
    
    description = issue.get('description', '')
    if description:
        # Format description with proper indentation
        for line in description.split('\n'):
            print(f"  {line}")
    else:
        print("  (No description provided)")
    
    print("="*60)
