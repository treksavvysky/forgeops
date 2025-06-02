"""
Repository Manager - Handles repository validation and management
"""

import json
import re
from pathlib import Path


class RepositoryManager:
    def __init__(self, repos_file="repos.json"):
        self.repos_file = Path(repos_file)
        self._init_repos_registry()
    
    def _init_repos_registry(self):
        """Initialize the repositories registry with some default repos."""
        if not self.repos_file.exists():
            default_repos = [
                "jules-dev-kit",
                "my-app", 
                "backend-api",
                "frontend-web",
                "mobile-app"
            ]
            with open(self.repos_file, 'w') as f:
                json.dump({"repositories": default_repos}, f, indent=2)
    
    def load_repositories(self):
        """Load the list of known repositories."""
        try:
            with open(self.repos_file, 'r') as f:
                data = json.load(f)
                return data.get("repositories", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading repositories: {e}")
            return []
    
    def validate_repo_name(self, repo_name):
        """Validate repository name against naming conventions."""
        # Check for basic naming conventions (letters, numbers, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', repo_name):
            return False, "Repository name can only contain letters, numbers, hyphens, and underscores"
        
        # Check length
        if len(repo_name) < 2:
            return False, "Repository name must be at least 2 characters long"
        
        if len(repo_name) > 50:
            return False, "Repository name must be 50 characters or less"
        
        return True, ""
    
    def suggest_repositories(self, user_input):
        """Suggest similar repository names if user input doesn't match exactly."""
        repos = self.load_repositories()
        suggestions = []
        
        user_lower = user_input.lower()
        
        for repo in repos:
            # Exact match
            if repo.lower() == user_lower:
                return True, []
            
            # Partial match or similar
            if user_lower in repo.lower() or repo.lower() in user_lower:
                suggestions.append(repo)
        
        return False, suggestions
    
    def add_repository(self, repo_name):
        """Add a new repository to the registry."""
        repos = self.load_repositories()
        if repo_name not in repos:
            repos.append(repo_name)
            repos.sort()  # Keep them sorted
            
            with open(self.repos_file, 'w') as f:
                json.dump({"repositories": repos}, f, indent=2)
            return True
        return False
