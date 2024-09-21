import time
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any
import logging
import colorlog
from dataclasses import dataclass
from github import Github, RateLimitExceededException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create color formatter
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )

    # Console handler
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler("repo_finder.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

@dataclass
class RepoConfig:
    min_python_percentage: float = 70.0
    max_contributors: int = 2
    min_stars: int = 5
    max_repos: int = 100
    recent_days: int = 5

class GitHubAPIWrapper:
    def __init__(self, token: str):
        self.github = Github(token)

    def get_user_repos(self):
        return self.github.get_user().get_repos()

    def get_rate_limit(self):
        return self.github.get_rate_limit()

class RepoAnalyzer:
    @staticmethod
    def get_language_percentages(repo) -> Dict[str, float]:
        languages = repo.get_languages()
        total = sum(languages.values())
        return {lang: (count / total) * 100 for lang, count in languages.items()}

    @staticmethod
    def is_likely_not_third_party(repo) -> bool:
        files = [file.name for file in repo.get_contents("")]
        return "setup.py" not in files and "requirements.txt" not in files

    @staticmethod
    def has_recent_commits(repo, days: int) -> bool:
        five_days_ago = datetime.now() - timedelta(days=days)
        default_branch = repo.default_branch
        commits = repo.get_commits(sha=default_branch, since=five_days_ago)
        return next(commits, None) is not None

class RepoCriteria:
    def __init__(self, config: RepoConfig):
        self.config = config

    def meets_criteria(self, repo) -> bool:
        analyzer = RepoAnalyzer()

        contributors = len(list(repo.get_contributors()))
        if contributors > self.config.max_contributors:
            logger.info(f"  ├─ {repo.name}: Skip - {contributors} contributors")
            return False

        if repo.stargazers_count < self.config.min_stars:
            logger.info(f"  ├─ {repo.name}: Skip - {repo.stargazers_count} stars")
            return False

        python_percentage = analyzer.get_language_percentages(repo).get('Python', 0)
        if python_percentage < self.config.min_python_percentage:
            logger.info(f"  ├─ {repo.name}: Skip - {python_percentage:.2f}% Python")
            return False

        if not analyzer.is_likely_not_third_party(repo):
            logger.info(f"  ├─ {repo.name}: Skip - Likely third-party")
            return False

        if not analyzer.has_recent_commits(repo, days=self.config.recent_days):
            logger.info(f"  ├─ {repo.name}: Skip - No recent commits")
            return False

        return True

class RepoFinder:
    def __init__(self, api_wrapper: GitHubAPIWrapper, criteria: RepoCriteria, config: RepoConfig):
        self.api_wrapper = api_wrapper
        self.criteria = criteria
        self.config = config

    def find_python_repos(self) -> List[Dict[str, Any]]:
        python_repos = []
        repo_count = 0

        logger.info("Searching for repositories:")
        logger.info(f"  Python > {self.config.min_python_percentage}%")
        logger.info(f"  Contributors <= {self.config.max_contributors}")
        logger.info(f"  Stars >= {self.config.min_stars}")
        logger.info(f"  Max repos = {self.config.max_repos}")
        logger.info(f"  Active within {self.config.recent_days} days")

        for repo in self.api_wrapper.get_user_repos():
            try:
                if repo_count >= self.config.max_repos:
                    logger.info(f"Max repos ({self.config.max_repos}) reached. Stopping.")
                    break

                if self.criteria.meets_criteria(repo):
                    python_repos.append(self.create_repo_dict(repo))
                    repo_count += 1
                    logger.info(f"  └─ {repo.name}: Added - Total: {repo_count}")

            except RateLimitExceededException:
                self.handle_rate_limit()
            except Exception as e:
                logger.error(f"  ├─ {repo.name}: Error - {str(e)}")

        logger.info(f"Search complete. Found {len(python_repos)} repos.")
        return python_repos

    def create_repo_dict(self, repo) -> Dict[str, Any]:
        return {
            'name': repo.name,
            'url': repo.html_url,
            'python_percentage': RepoAnalyzer.get_language_percentages(repo).get('Python', 0),
            'contributors': len(list(repo.get_contributors())),
            'stars': repo.stargazers_count,
            'default_branch': repo.default_branch
        }

    def handle_rate_limit(self):
        rate_limit = self.api_wrapper.get_rate_limit()
        reset_timestamp = rate_limit.core.reset.timestamp()
        sleep_time = reset_timestamp - time.time()
        logger.warning(f"Rate limit hit. Sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time + 1)  # Add 1 second buffer

def main():
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.error("GitHub token not found. Set GITHUB_TOKEN env var.")
        return

    config = RepoConfig()
    api_wrapper = GitHubAPIWrapper(github_token)
    criteria = RepoCriteria(config)
    finder = RepoFinder(api_wrapper, criteria, config)

    logger.info("Starting repo search...")
    repos = finder.find_python_repos()

    logger.info("Found repositories:")
    for repo in repos:
        logger.info(f"  {repo['name']}:")
        logger.info(f"    URL: {repo['url']}")
        logger.info(f"    Python: {repo['python_percentage']:.2f}%")
        logger.info(f"    Contributors: {repo['contributors']}")
        logger.info(f"    Stars: {repo['stars']}")
        logger.info(f"    Branch: {repo['default_branch']}")

if __name__ == "__main__":
    main()