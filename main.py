#!/usr/bin/env python3
"""
ForgeOps - Issue Tracking System
CLI entry point for issue management commands.
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from commands.create_issue import create_issue
from commands.list_issues import list_issues
from commands.view_issue import view_issue
from commands.list_repos import list_repos
from commands.add_repo import add_repo


def show_help():
    """Display help information."""
    print("ForgeOps - Issue Tracker")
    print("\nIssue Management:")
    print("  python main.py create-issue              Create a new issue")
    print("  python main.py list-issues               List all issues")
    print("  python main.py list-issues --repo <n>    List issues for specific repository")
    print("  python main.py view-issue <ISSUE-ID>     View detailed issue information")
    print("\nRepository Management:")
    print("  python main.py list-repos                List all registered repositories")
    print("  python main.py add-repo <repo-name>      Add a new repository to registry")
    print("\nExamples:")
    print("  python main.py create-issue")
    print("  python main.py list-issues")
    print("  python main.py list-issues --repo jules-dev-kit")
    print("  python main.py view-issue ISSUE-001")
    print("  python main.py list-repos")
    print("  python main.py add-repo my-new-project")


def main():
    """Main entry point for the CLI application."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "create-issue":
            create_issue()
        
        elif command == "list-issues":
            # Check for repository filter
            repo_filter = None
            if len(sys.argv) > 2:
                if sys.argv[2] == "--repo" and len(sys.argv) > 3:
                    repo_filter = sys.argv[3]
                else:
                    print("Invalid arguments for list-issues command.")
                    print("Usage: python main.py list-issues [--repo <repository-name>]")
                    sys.exit(1)
            
            list_issues(repo_filter)
        
        elif command == "view-issue":
            if len(sys.argv) < 3:
                print("Missing issue ID.")
                print("Usage: python main.py view-issue <ISSUE-ID>")
                print("Example: python main.py view-issue ISSUE-001")
                sys.exit(1)
            
            issue_id = sys.argv[2]
            view_issue(issue_id)
        
        elif command == "list-repos":
            list_repos()
        
        elif command == "add-repo":
            if len(sys.argv) < 3:
                print("Missing repository name.")
                print("Usage: python main.py add-repo <repo-name>")
                print("Example: python main.py add-repo my-new-project")
                sys.exit(1)
            
            repo_name = sys.argv[2]
            add_repo(repo_name)
        
        elif command in ["help", "--help", "-h"]:
            show_help()
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: create-issue, list-issues, view-issue, list-repos, add-repo")
            print("Use 'python main.py help' for more information.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
