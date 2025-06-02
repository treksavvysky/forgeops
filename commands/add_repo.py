"""
Add Repository Command - Add a new repository to the registry
"""

import sys

from core.repository_manager import RepositoryManager


def add_repo(repo_name):
    """Add a new repository to the registry."""
    repo_manager = RepositoryManager()
    
    # Validate repository name
    is_valid, error_msg = repo_manager.validate_repo_name(repo_name)
    if not is_valid:
        print(f"Invalid repository name: {error_msg}")
        return
    
    try:
        # Check if repo already exists
        existing_repos = repo_manager.load_repositories()
        if repo_name in existing_repos:
            print(f"Repository '{repo_name}' already exists in registry.")
            return
        
        # Add the repository
        success = repo_manager.add_repository(repo_name)
        
        if success:
            print(f"✅ Repository '{repo_name}' added successfully!")
            
            # Show updated count
            updated_repos = repo_manager.load_repositories()
            print(f"📊 Registry now contains {len(updated_repos)} repositories.")
            print("Use 'python main.py list-repos' to see all repositories.")
        else:
            print(f"❌ Failed to add repository '{repo_name}'.")
    
    except Exception as e:
        print(f"Error adding repository: {e}")
        sys.exit(1)
