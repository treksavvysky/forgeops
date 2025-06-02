"""
Create Issue Command - Interactive issue creation
"""

import sys
from datetime import datetime

from core.issue_tracker import IssueTracker


def create_issue():
    """Interactive issue creation process."""
    tracker = IssueTracker()
    
    print("Creating a new issue...")
    print("Press Ctrl+C at any time to cancel.\n")
    
    # Get issue title
    title = tracker.validator.get_user_input("Issue title: ", required=True)
    
    # Get repository name with validation and suggestions
    while True:
        repo_name = tracker.validator.get_user_input(
            "Repository name: ", 
            required=True, 
            validator=tracker.repo_manager.validate_repo_name
        )
        
        confirmed_repo = tracker.confirm_repository(repo_name)
        if confirmed_repo:
            repo_name = confirmed_repo
            break
        
        print("Please enter a repository name.\n")
    
    # Get description (optional)
    description = tracker.validator.get_user_input("Description (optional): ", required=False)
    
    # Generate issue data
    issue_id = tracker.file_manager.get_next_issue_id()
    issue_data = {
        "id": issue_id,
        "title": title,
        "description": description,
        "repository": repo_name,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Show preview and confirm
    tracker.display_issue_preview(issue_data)
    
    try:
        confirm = input("\nCreate this issue? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            issue_file = tracker.file_manager.save_issue(issue_data)
            print(f"\n✅ Issue {issue_id} created successfully!")
            print(f"📁 Saved to: {issue_file}")
        else:
            print("\n❌ Issue creation cancelled.")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
