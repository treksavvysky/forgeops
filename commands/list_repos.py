"""
List Repositories Command - Display all repositories in the registry
"""

from core.repository_manager import RepositoryManager


def list_repos():
    """List all repositories in the registry."""
    repo_manager = RepositoryManager()
    
    try:
        repos = repo_manager.load_repositories()
    except Exception as e:
        print(f"Error loading repositories: {e}")
        return
    
    if not repos:
        print("No repositories found in registry.")
        print("Use 'python main.py add-repo <name>' to add repositories.")
        return
    
    # Display header
    print("\n" + "="*50)
    print("REGISTERED REPOSITORIES")
    print("="*50)
    
    # Display repositories
    for i, repo in enumerate(repos, 1):
        print(f"{i:2d}. {repo}")
    
    print("="*50)
    print(f"Total: {len(repos)} repository(ies)")
    print("\nUse 'python main.py add-repo <name>' to add more repositories.")
