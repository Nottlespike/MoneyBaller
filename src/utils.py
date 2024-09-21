from datetime import datetime
from typing import Dict, Any, List
import logging
from github import RateLimitExceededException

logger = logging.getLogger(__name__)

def format_date(date: datetime) -> str:
    return date.strftime("%Y-%m-%d %H:%M:%S")

def truncate_string(s: str, max_length: int = 50) -> str:
    return (s[:max_length] + '...') if len(s) > max_length else s

def handle_github_exception(e: Exception):
    if isinstance(e, RateLimitExceededException):
        logger.error("GitHub API rate limit exceeded. Please wait or use a different token.")
    elif hasattr(e, 'status') and e.status == 401:
        logger.error("GitHub API authentication failed. Please check your token.")
    elif hasattr(e, 'status') and e.status == 403:
        logger.error("GitHub API access forbidden. Please check your token permissions.")
    else:
        logger.error(f"An unexpected error occurred: {str(e)}")

def print_repo_info(repo: Dict[str, Any]):
    logger.info(f"  {repo['name']}:")
    logger.info(f"    URL: {repo['url']}")
    logger.info(f"    Languages:")
    for lang, percentage in repo['language_percentages'].items():
        logger.info(f"      {lang}: {percentage:.2f}%")
    logger.info(f"    Contributors: {len(repo['contributors'])}")
    logger.info(f"    Stars: {repo['stars']}")
    logger.info(f"    Forks: {repo['forks']}")
    logger.info(f"    Created: {format_date(repo['created'])}")
    logger.info(f"    Last Updated: {format_date(repo['updated'])}")
    logger.info(f"    Last Pushed: {format_date(repo['pushed'])}")
    logger.info(f"    Size: {repo['size']} KB")
    logger.info(f"    Default Branch: {repo['default_branch']}")
    logger.info(f"    Topics: {', '.join(repo['topics'])}")
    logger.info(f"    Public: {repo['is_public']}")
    logger.info(f"    Owner: {repo['owner_info']['login']} ({repo['owner_info']['type']})")
    if repo['owner_info']['type'] == 'User':
        logger.info(f"    Owner Organizations: {', '.join([org['login'] for org in repo['owner_info']['organizations']])}")
    logger.info(f"    Recent Commits:")
    for commit in repo['commit_history'][:5]:  # Show only the 5 most recent commits
        logger.info(f"      {format_date(commit['date'])}: {truncate_string(commit['message'])} by {commit['author']}")

def print_shared_contributors(shared_contributors: Dict[str, List[str]]):
    for contributor, repos in shared_contributors.items():
        logger.info(f"  {contributor}:")
        for repo in repos:
            logger.info(f"    - {repo}")

def save_results_to_file(repos: List[Dict[str, Any]], shared_contributors: Dict[str, List[str]]):
    with open('github_repo_analysis_results.txt', 'w') as f:
        f.write("Found Repositories:\n\n")
        for repo in repos:
            f.write(f"{repo['name']}:\n")
            f.write(f"  URL: {repo['url']}\n")
            f.write(f"  Languages:\n")
            for lang, percentage in repo['language_percentages'].items():
                f.write(f"    {lang}: {percentage:.2f}%\n")
            f.write(f"  Contributors: {len(repo['contributors'])}\n")
            f.write(f"  Stars: {repo['stars']}\n")
            f.write(f"  Forks: {repo['forks']}\n")
            f.write(f"  Created: {format_date(repo['created'])}\n")
            f.write(f"  Last Updated: {format_date(repo['updated'])}\n")
            f.write(f"  Last Pushed: {format_date(repo['pushed'])}\n")
            f.write(f"  Size: {repo['size']} KB\n")
            f.write(f"  Default Branch: {repo['default_branch']}\n")
            f.write(f"  Topics: {', '.join(repo['topics'])}\n")
            f.write(f"  Public: {repo['is_public']}\n")
            f.write(f"  Owner: {repo['owner_info']['login']} ({repo['owner_info']['type']})\n")
            if repo['owner_info']['type'] == 'User':
                f.write(f"  Owner Organizations: {', '.join([org['login'] for org in repo['owner_info']['organizations']])}\n")
            f.write(f"  Recent Commits:\n")
            for commit in repo['commit_history'][:5]:
                f.write(f"    {format_date(commit['date'])}: {truncate_string(commit['message'])} by {commit['author']}\n")
            f.write("\n")

        f.write("\nShared Contributors:\n\n")
        for contributor, repos in shared_contributors.items():
            f.write(f"{contributor}:\n")
            for repo in repos:
                f.write(f"  - {repo}\n")
            f.write("\n")

    logger.info(f"Results saved to github_repo_analysis_results.txt")