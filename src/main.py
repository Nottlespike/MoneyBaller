import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from config import SearchConfig, RepoConfig, Language, SortCriteria, SortOrder
from github_api import GitHubAPIWrapper
from repo_finder import RepoFinder, RepoCriteria
from utils import print_repo_info, print_shared_contributors, save_results_to_file, handle_github_exception
from logging_setup import setup_logger

logger = setup_logger()

def main():
    all_contributors = []
    try:
        # Load environment variables
        load_dotenv()

        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise ValueError("GitHub token not found. Set GITHUB_TOKEN env var.")

        # Create configuration (hard-coded)
        search_config = SearchConfig(
            repo_config=RepoConfig(
                min_language_percentage=60.0,
                max_contributors=3,
                min_stars=100,  # Increased for global search
                max_repos=100,  # Increased for global search
                recent_days=30  # Increased for global search
            ),
            github_token=github_token,
            excluded_repos=[],  # Removed personal repo exclusion
            included_languages=[Language.PYTHON, Language.JAVASCRIPT],
            sort_by=SortCriteria.STARS,
            sort_order=SortOrder.DESCENDING,
            min_repo_size=100,  # 100 KB
            max_repo_size=10000,  # 10 MB
            include_forks=False,
            created_after=datetime.now() - timedelta(days=365),  # Repos created in the last year
            pushed_after=datetime.now() - timedelta(days=30),  # Repos pushed to in the last month
            topics=["machine-learning", "data-science"],
            license="MIT",
            is_public=True
        )

        # Initialize components
        api_wrapper = GitHubAPIWrapper(search_config.github_token, search_config)  # Updated to include search_config
        criteria = RepoCriteria(search_config)
        finder = RepoFinder(api_wrapper, criteria, search_config)

        # Find repos and analyze
        logger.info("Starting global repo search...")
        repos = finder.find_repos_global()  # Changed to use global search
        logger.info("Analyzing shared contributors...")
        shared_contributors = finder.find_shared_contributors(repos)

        # Print and save results
        logger.info("Found repositories:")
        for repo in repos:
            print_repo_info(repo)
        logger.info("Shared contributors:")
        print_shared_contributors(shared_contributors)

        # Save results to a file
        save_results_to_file(repos, shared_contributors)

    except Exception as e:
        handle_github_exception(e)

if __name__ == "__main__":
    main()