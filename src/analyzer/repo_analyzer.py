import os
import json
from pathlib import Path
from collections import defaultdict
from github.Repository import Repository

import re
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def load_gitignore(repo_path):
    gitignore_path = os.path.join(repo_path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            return PathSpec.from_lines(GitWildMatchPattern, f)
    return None

def should_analyze_file(file_path, repo_path, gitignore_spec):
    if os.path.basename(file_path) == '__init__.py':
        return False
    if gitignore_spec:
        relative_path = os.path.relpath(file_path, repo_path)
        if gitignore_spec.match_file(relative_path):
            return False
    return True

def calculate_file_importance(file_path, repo_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    relative_path = os.path.relpath(file_path, repo_path)
    
    # Base importance score
    importance = 100
    
    # Adjust based on file name
    if file_name in ['main.py', 'app.py', 'run.py']:
        importance += 50
    elif 'test' in file_name.lower():
        importance -= 20
    elif file_name.startswith('utils'):
        importance -= 10
    
    # Adjust based on directory depth (prefer files closer to root)
    depth = len(Path(relative_path).parts) - 1
    importance -= depth * 5
    
    # Adjust based on file size (prefer medium-sized files)
    if file_size < 1000:  # Small files (less than 1KB)
        importance -= 10
    elif file_size > 100000:  # Large files (more than 100KB)
        importance -= 20
    
    # Bonus for files that likely contain important logic
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        if re.search(r'class.*\(.*\):', content):  # Contains class definitions
            importance += 20
        if re.search(r'def.*\(.*\):', content):  # Contains function definitions
            importance += 10
        if 'import' in content:  # Contains imports
            importance += 5
    
    return max(importance, 0)  # Ensure non-negative importance

def analyze_repository(repo_path):
    gitignore_spec = load_gitignore(repo_path)
    file_importance = defaultdict(int)
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if should_analyze_file(file_path, repo_path, gitignore_spec):
                    importance = calculate_file_importance(file_path, repo_path)
                    file_importance[file_path] = importance
    
    # Sort files by importance and get top 20
    top_files = sorted(file_importance.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return top_files


if __name__ == "__main__":
    pass
    #main()