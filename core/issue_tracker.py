"""
Issue Tracker - Main class for managing issues
"""

import sys
from datetime import datetime

from core.repository_manager import RepositoryManager
from core.file_manager import FileManager
from utils.validators import InputValidator


class IssueTracker:
    def __init__(self):
        self.repo_manager = RepositoryManager()
        self.file_manager = FileManager()
        self.validator = InputValidator()
    
    def confirm_repository(self, repo_name):
        """Confirm repository name and suggest alternatives if needed."""
        repos = self.repo_manager.load_repositories()
        
        # Check if repo exists in registry
        if repo_name in repos:
            return repo_name
        
        # Check for similar repositories
        exact_match, suggestions = self.repo_manager.suggest_repositories(repo_name)
        
        if suggestions:
            print(f"\nRepository '{repo_name}' not found in registry.")
            print("Did you mean one of these?")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
            print(f"  {len(suggestions) + 1}. Use '{repo_name}' anyway")
            print(f"  {len(suggestions) + 2}. Enter a different name")
            
            try:
                choice = input(f"\nSelect option (1-{len(suggestions) + 2}): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(suggestions):
                    return suggestions[choice_num - 1]
                elif choice_num == len(suggestions) + 1:
                    return repo_name
                elif choice_num == len(suggestions) + 2:
                    return None  # Signal to ask for name again
                else:
                    print("Invalid selection.")
                    return None
                    
            except (ValueError, KeyboardInterrupt):
                if KeyboardInterrupt:
                    print("\n\nOperation cancelled by user.")
                    sys.exit(0)
                print("Invalid selection.")
                return None
        else:
            # No suggestions, ask if they want to use it anyway
            try:
                use_anyway = input(f"Repository '{repo_name}' not found. Use it anyway? (y/N): ").strip().lower()
                if use_anyway in ['y', 'yes']:
                    return repo_name
                else:
                    return None
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user.")
                sys.exit(0)
    
    def display_issue_preview(self, issue_data):
        """Display issue details for user confirmation."""
        print("\n" + "="*50)
        print("ISSUE PREVIEW")
        print("="*50)
        print(f"Issue ID:    {issue_data['id']}")
        print(f"Title:       {issue_data['title']}")
        print(f"Repository:  {issue_data['repository']}")
        print(f"Description: {issue_data['description'] or '(No description)'}")
        print(f"Created:     {issue_data['created_at']}")
        print("="*50)
