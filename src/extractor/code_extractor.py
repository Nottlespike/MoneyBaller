import os
import re
import requests
from github import Github, GithubException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize GitHub client
g = Github(os.getenv('GITHUB_TOKEN'))

def parse_repo_results(file_path):
    repos = []
    with open(file_path, 'r') as f:
        content = f.read()
        # Use regex to find all repository URLs
        matches = re.findall(r'URL: https://github\.com/([^/]+/[^/\n]+)', content)
        repos = [match for match in matches]
    return repos

def download_py_files(repo_name, output_dir):
    try:
        # Get the repository
        repo = g.get_repo(repo_name)
        
        # Create a directory for the repository
        repo_dir = os.path.join(output_dir, repo.name)
        os.makedirs(repo_dir, exist_ok=True)
        
        # Get all Python files in the repository
        contents = repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            elif file_content.name.endswith('.py'):
                # Download the file
                file_path = os.path.join(repo_dir, file_content.path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(file_content.decoded_content)
                print(f"Downloaded: {file_path}")
    
    except GithubException as e:
        print(f"Error accessing repository {repo_name}: {e}")

def main():
    # Path to the results file
    results_file = "github_repo_analysis_results.txt"
    
    # Parse repositories from the results file
    repos = parse_repo_results(results_file)
    
    if not repos:
        print("No repositories found in the results file.")
        return
    
    # Output directory
    output_dir = os.path.join("data", "github_repos_python_files")
    
    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Download Python files from each repository
    for repo in repos:
        print(f"Downloading Python files from {repo}...")
        download_py_files(repo, output_dir)
    
    print("Download completed.")

if __name__ == "__main__":
    main()