from github import RateLimitExceededException
from typing import List, Dict, Any
import time
import logging
from datetime import datetime, timedelta
from config import SearchConfig, SortOrder
from github_api import GitHubAPIWrapper
from repo_analyzer import RepoAnalyzer

logger = logging.getLogger(__name__)

class RepoCriteria:
    def __init__(self, config: SearchConfig):
        self.config = config

    def meets_criteria(self, repo) -> bool:
        analyzer = RepoAnalyzer()

        if repo.name in self.config.excluded_repos:
            logger.info(f"  ├─ {repo.name}: Skip - Excluded repo")
            return False

        contributors = len(list(repo.get_contributors()))
        if contributors > self.config.repo_config.max_contributors:
            logger.info(f"  ├─ {repo.name}: Skip - {contributors} contributors")
            return False

        if repo.stargazers_count < self.config.repo_config.min_stars:
            logger.info(f"  ├─ {repo.name}: Skip - {repo.stargazers_count} stars")
            return False

        language_percentages = analyzer.get_language_percentages(repo)
        for lang in self.config.included_languages:
            if language_percentages.get(lang.value, 0) < self.config.repo_config.min_language_percentage:
                logger.info(f"  ├─ {repo.name}: Skip - {language_percentages.get(lang.value, 0):.2f}% {lang.value}")
                return False

        if not analyzer.is_likely_not_third_party(repo):
            logger.info(f"  ├─ {repo.name}: Skip - Likely third-party")
            return False

        if not analyzer.has_recent_commits(repo, days=self.config.repo_config.recent_days):
            logger.info(f"  ├─ {repo.name}: Skip - No recent commits")
            return False

        if self.config.min_repo_size and repo.size < self.config.min_repo_size:
            logger.info(f"  ├─ {repo.name}: Skip - Too small")
            return False

        if self.config.max_repo_size and repo.size > self.config.max_repo_size:
            logger.info(f"  ├─ {repo.name}: Skip - Too large")
            return False

        if not self.config.include_forks and repo.fork:
            logger.info(f"  ├─ {repo.name}: Skip - Fork")
            return False

        if self.config.created_after and repo.created_at < self.config.created_after:
            logger.info(f"  ├─ {repo.name}: Skip - Too old")
            return False

        if self.config.pushed_after and repo.pushed_at < self.config.pushed_after:
            logger.info(f"  ├─ {repo.name}: Skip - Not recently pushed")
            return False

        if self.config.topics and not all(topic in repo.get_topics() for topic in self.config.topics):
            logger.info(f"  ├─ {repo.name}: Skip - Missing required topics")
            return False

        if self.config.is_public is not None and repo.private != (not self.config.is_public):
            logger.info(f"  ├─ {repo.name}: Skip - Wrong visibility")
            return False

        consistent_contributors = self.get_consistent_contributors(repo)
        if not consistent_contributors:
            logger.info(f"  ├─ {repo.name}: Skip - No consistent contributors")
            return False

        return True

    def get_consistent_contributors(self, repo) -> List[Dict[str, Any]]:
        consistent_contributors = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2 years

        for contributor in repo.get_contributors():
            commits = repo.get_commits(author=contributor, since=start_date, until=end_date)
            commit_months = set()
            for commit in commits:
                commit_months.add((commit.commit.author.date.year, commit.commit.author.date.month))
            
            if len(commit_months) >= 17:  # At least 70% of 24 months
                consistent_contributors.append({
                    'login': contributor.login,
                    'contributions': contributor.contributions,
                    'active_months': len(commit_months)
                })

        return consistent_contributors

class RepoFinder:
    def __init__(self, api_wrapper: GitHubAPIWrapper, criteria: RepoCriteria, config: SearchConfig):
        self.api_wrapper = api_wrapper
        self.criteria = criteria
        self.config = config

    def find_repos(self) -> List[Dict[str, Any]]:
        all_repos = []
        matching_repos = []
        repo_count = 0
        logger.info("Searching for repositories:")
        logger.info(f"  Languages: {', '.join([lang.value for lang in self.config.included_languages])}")
        logger.info(f"  Min percentage: {self.config.repo_config.min_language_percentage}%")
        logger.info(f"  Max contributors: {self.config.repo_config.max_contributors}")
        logger.info(f"  Min stars: {self.config.repo_config.min_stars}")
        logger.info(f"  Max repos: {self.config.repo_config.max_repos}")
        logger.info(f"  Active within: {self.config.repo_config.recent_days} days")
        logger.info(f"  Sort by: {self.config.sort_by.value} ({self.config.sort_order.value}ending)")
        logger.info("  Consistent contributors: Active in at least 70% of months over past 2 years")
        if self.config.excluded_repos:
            logger.info(f"  Excluded repos: {', '.join(self.config.excluded_repos)}")

        for repo in self.api_wrapper.get_user_repos():
            try:
                if repo_count >= self.config.repo_config.max_repos:
                    logger.info(f"Max repos ({self.config.repo_config.max_repos}) reached. Stopping.")
                    break

                repo_dict = self.create_repo_dict(repo)
                meets_criteria = self.criteria.meets_criteria(repo)
                repo_dict['meets_criteria'] = meets_criteria

                all_repos.append(repo_dict)
                if meets_criteria:
                    matching_repos.append(repo_dict)

                repo_count += 1
                logger.info(f"  {'└─' if meets_criteria else '├─'} {repo.name}: {'Meets criteria' if meets_criteria else 'Does not meet criteria'} - Total: {repo_count}")
                self.print_repo_details(repo_dict)

            except RateLimitExceededException:
                self.handle_rate_limit()
            except Exception as e:
                logger.error(f"  ├─ {repo.name}: Error - {str(e)}")

        # Sort the results
        all_repos.sort(
            key=lambda x: x[self.config.sort_by.value],
            reverse=(self.config.sort_order == SortOrder.DESCENDING)
        )

        logger.info(f"Search complete. Found {len(all_repos)} total repos, {len(matching_repos)} meeting all criteria.")
        return all_repos

    def print_repo_details(self, repo: Dict[str, Any]):
        logger.info(f"\nDetailed information for {repo['name']}:")
        logger.info(f"  URL: {repo['url']}")
        logger.info(f"  Meets all criteria: {'Yes' if repo['meets_criteria'] else 'No'}")
        logger.info(f"  Stars: {repo['stars']}, Forks: {repo['forks']}")
        logger.info(f"  Created: {repo['created']}, Last pushed: {repo['pushed']}")
        logger.info(f"  Size: {repo['size']} KB")
        logger.info(f"  Topics: {', '.join(repo['topics'])}")
        logger.info(f"  Public: {repo['is_public']}")
        
        logger.info("  Language Percentages:")
        for lang, percentage in repo['language_percentages'].items():
            logger.info(f"    {lang}: {percentage:.2f}%")
        
        logger.info("  Contributors:")
        for contributor in repo['contributors']:
            logger.info(f"    {contributor['login']}: {contributor['contributions']} contributions")
        
        logger.info("  Consistent Contributors:")
        for contributor in repo['consistent_contributors']:
            logger.info(f"    {contributor['login']}: Active for {contributor['active_months']} months")
        
        logger.info("  Recent Commits:")
        for commit in repo['commit_history'][:10]:  # Show only the 10 most recent commits
            logger.info(f"    {commit['date']}: {commit['message'][:50]}... by {commit['author']}")
            logger.info(f"      Additions: {commit['additions']}, Deletions: {commit['deletions']}")

    def create_repo_dict(self, repo) -> Dict[str, Any]:
        consistent_contributors = self.criteria.get_consistent_contributors(repo)
        commit_history = self.get_detailed_commit_history(repo)
        return {
            'name': repo.name,
            'url': repo.html_url,
            'language_percentages': RepoAnalyzer.get_language_percentages(repo),
            'contributors': self.get_detailed_contributors(repo),
            'consistent_contributors': consistent_contributors,
            'stars': repo.stargazers_count,
            'forks': repo.forks_count,
            'updated': repo.updated_at,
            'created': repo.created_at,
            'pushed': repo.pushed_at,
            'size': repo.size,
            'default_branch': repo.default_branch,
            'topics': repo.get_topics(),
            'is_public': not repo.private,
            'commit_history': commit_history,
            'owner_info': self.get_repo_owner_info(repo)
        }
        

    def get_detailed_commit_history(self, repo, max_commits: int = 50) -> List[Dict[str, Any]]:
        commits = []
        for commit in repo.get_commits()[:max_commits]:
            commits.append({
                'sha': commit.sha,
                'author': commit.author.login if commit.author else 'Unknown',
                'date': commit.commit.author.date,
                'message': commit.commit.message,
                'additions': commit.stats.additions,
                'deletions': commit.stats.deletions,
            })
        return commits

    def get_detailed_contributors(self, repo) -> List[Dict[str, Any]]:
        return [
            {
                'login': c.login,
                'contributions': c.contributions,
                'url': c.html_url,
                'type': c.type,
            } for c in repo.get_contributors()
        ]

    def print_repo_details(self, repo: Dict[str, Any]):
        logger.info(f"\nDetailed information for {repo['name']}:")
        logger.info(f"  URL: {repo['url']}")
        logger.info(f"  Stars: {repo['stars']}, Forks: {repo['forks']}")
        logger.info(f"  Created: {repo['created']}, Last pushed: {repo['pushed']}")
        logger.info(f"  Size: {repo['size']} KB")
        logger.info(f"  Topics: {', '.join(repo['topics'])}")
        logger.info(f"  Public: {repo['is_public']}")
        
        logger.info("  Language Percentages:")
        for lang, percentage in repo['language_percentages'].items():
            logger.info(f"    {lang}: {percentage:.2f}%")
        
        logger.info("  Contributors:")
        for contributor in repo['contributors']:
            logger.info(f"    {contributor['login']}: {contributor['contributions']} contributions")
        
        logger.info("  Consistent Contributors:")
        for contributor in repo['consistent_contributors']:
            logger.info(f"    {contributor['login']}: Active for {contributor['active_months']} months")
        
        logger.info("  Recent Commits:")
        for commit in repo['commit_history'][:10]:  # Show only the 10 most recent commits
            logger.info(f"    {commit['date']}: {commit['message'][:50]}... by {commit['author']}")
            logger.info(f"      Additions: {commit['additions']}, Deletions: {commit['deletions']}")

    def get_repo_owner_info(self, repo) -> Dict[str, Any]:
        owner = repo.owner
        return {
            'login': owner.login,
            'type': owner.type,
            'organizations': self.api_wrapper.get_user_organizations(owner.login) if owner.type == 'User' else []
        }

    def find_shared_contributors(self, repos: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        all_contributors = {}
        for repo in repos:
            repo_contributors = set(c['login'] for c in repo['contributors'])
            for contributor in repo_contributors:
                if contributor in all_contributors:
                    all_contributors[contributor].append(repo['name'])
                else:
                    all_contributors[contributor] = [repo['name']]
        
        return {c: repos for c, repos in all_contributors.items() if len(repos) > 1}

    def handle_rate_limit(self):
        rate_limit = self.api_wrapper.get_rate_limit()
        reset_timestamp = rate_limit.core.reset.timestamp()
        sleep_time = reset_timestamp - time.time()
        logger.warning(f"Rate limit hit. Sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time + 1)  # Add 1 second buffer