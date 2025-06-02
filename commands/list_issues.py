"""
List Issues Command - Display all issues or filter by repository
"""

from datetime import datetime

from core.file_manager import FileManager
from utils.helpers import truncate_text, format_datetime


def list_issues(repo_filter=None):
    """List all issues, optionally filtered by repository."""
    file_manager = FileManager()
    
    try:
        issues = file_manager.load_all_issues()
    except Exception as e:
        print(f"Error loading issues: {e}")
        return
    
    if not issues:
        print("No issues found.")
        return
    
    # Filter by repository if specified
    if repo_filter:
        issues = [issue for issue in issues if issue['repository'].lower() == repo_filter.lower()]
        if not issues:
            print(f"No issues found for repository '{repo_filter}'.")
            return
    
    # Display header
    print("\n" + "="*80)
    if repo_filter:
        print(f"ISSUES FOR REPOSITORY: {repo_filter}")
    else:
        print("ALL ISSUES")
    print("="*80)
    
    # Display issues in a table format
    for issue in issues:
        # Truncate title and description for table display
        title = truncate_text(issue['title'], 50)
        description = issue.get('description', '')
        desc_preview = truncate_text(description, 30)
        
        # Format created date
        try:
            created_date = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            date_str = created_date.strftime('%Y-%m-%d %H:%M')
        except (ValueError, KeyError):
            date_str = "Unknown"
        
        print(f"{issue['id']:<12} | {issue['repository']:<20} | {date_str:<16} | {title}")
        if desc_preview:
            print(f"{'':12} | {'':20} | {'':16} | └─ {desc_preview}")
        print("-" * 80)
    
    print(f"\nTotal: {len(issues)} issue(s)")
    print("\nUse 'python main.py view-issue <ISSUE-ID>' to see full details.")
