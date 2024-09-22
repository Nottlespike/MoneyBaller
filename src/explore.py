# return "starting point" repositories
# this is for user's who don't have a target repository they have in mind 
from dotenv import load_dotenv
from config import SearchConfig, RepoConfig, Language, SortCriteria, SortOrder
from datetime import datetime, timedelta
from github import Github
from github.NamedUser import NamedUser
from github.PaginatedList import PaginatedList
from github.Repository import Repository

import os
load_dotenv()

from datetime import datetime, timedelta
from typing import Dict, List, Any
from logging_setup import setup_logger

logger = setup_logger()
github_token = os.getenv('GITHUB_TOKEN')

class RepoAnalyzer:
    @staticmethod
    def get_language_percentages(repo) -> Dict[str, float]:
        languages = repo.get_languages()
        total = sum(languages.values())
        return {lang: (count / total) * 100 for lang, count in languages.items()}

    @staticmethod
    def get_commit_history(repo, max_commits: int = 30) -> List[Dict[str, Any]]:
        commits = []
        for commit in repo.get_commits()[:max_commits]:
            commits.append({
                'sha': commit.sha,
                'author': commit.author.login if commit.author else 'Unknown',
                'date': commit.commit.author.date,
                'message': commit.commit.message
            })
        return commits

def create_repo_dict(repo) -> Dict[str, Any]:
    print(dir(repo))
    contributors : List[NamedUser] = repo.get_contributors()
    return {
        'name': repo.name,
        'url': repo.html_url,
        'language_percentages': RepoAnalyzer.get_language_percentages(repo),
        'contributors': contributors,
        'stars': repo.stargazers_count,
        'forks': repo.forks_count,
        'updated': repo.updated_at,
        'created': repo.created_at,
        'pushed': repo.pushed_at,
        'size': repo.size,
        'default_branch': repo.default_branch,
        'topics': repo.get_topics(),
        'is_public': not repo.private,
        'owner_info': repo.owner
    }
    
def meets_criteria(config: SearchConfig, repo) -> bool:
    analyzer = RepoAnalyzer()
    contributors = len(list(repo.get_contributors()))
    if contributors > config.repo_config.max_contributors:
        logger.info(f"  ├─ {repo.name}: Skip - {contributors} contributors")
        return False

    if repo.stargazers_count > config.repo_config.max_stars:
        logger.info(f"  ├─ {repo.name}: Skip - {repo.stargazers_count} stars")
        return False

    language_percentages = analyzer.get_language_percentages(repo)
    for lang in config.included_languages:
        if language_percentages.get(lang.value, 0) < config.repo_config.min_language_percentage:
            logger.info(f"  ├─ {repo.name}: Skip - {language_percentages.get(lang.value, 0):.2f}% {lang.value}")
            return False

    if config.min_repo_size and repo.size < config.min_repo_size:
        logger.info(f"  ├─ {repo.name}: Skip - Too small")
        return False

    if config.max_repo_size and repo.size > config.max_repo_size:
        logger.info(f"  ├─ {repo.name}: Skip - Too large")
        return False

    if not config.include_forks and repo.fork:
        logger.info(f"  ├─ {repo.name}: Skip - Fork")
        return False

    if config.created_after and repo.created_at < config.created_after:
        logger.info(f"  ├─ {repo.name}: Skip - Too old")
        return False

    if config.is_public is not None and repo.private != (not config.is_public):
        logger.info(f"  ├─ {repo.name}: Skip - Wrong visibility")
        return False

    return True

def construct_search_query(config: SearchConfig) -> str:
    query_parts = []
    
    # Add language filter
    languages = " ".join(f"language:{lang.value}" for lang in config.included_languages)
    query_parts.append(languages)
    
    # Add star filter
    query_parts.append(f"stars:<={config.repo_config.max_stars}")
    
    # Add size filter
    if config.min_repo_size:
        query_parts.append(f"size:>={config.min_repo_size}")
    if config.max_repo_size:
        query_parts.append(f"size:<={config.max_repo_size}")
    
    # Add fork filter
    if not config.include_forks:
        query_parts.append("fork:false")
    
    # Add created date filter
    if config.created_after:
        created_after = config.created_after.strftime("%Y-%m-%d")
        query_parts.append(f"created:>={created_after}")
    
    # Add pushed date filter
    if config.pushed_after:
        pushed_after = config.pushed_after.strftime("%Y-%m-%d")
        query_parts.append(f"pushed:>={pushed_after}")
    
    # Add topics filter
    if config.topics:
        topics = " ".join(f"topic:{topic}" for topic in config.topics)
        query_parts.append(topics)
    
    # Add visibility filter
    if config.is_public is not None:
        query_parts.append("is:public" if config.is_public else "is:private")
    
    return " ".join(query_parts)

def print_repo_details(repo: Dict[str, Any]):
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
        logger.info(f"    {contributor.html_url}: {contributor.contributions} contributions")

# TODO user should be able to pass in
# each of the fields below
def explore_repos(limit=1) -> List[Dict]:
# Create configuration
    gh = Github(github_token)
    search_config = SearchConfig(
        repo_config=RepoConfig(
            min_language_percentage=60.0,
            max_contributors=30,
            max_stars=1000,  # Increased for global search
            max_repos=100,  # Increased for global search
            recent_days=30  # Increased for global search
        ),
        github_token=github_token,
        excluded_repos=[],  # Removed personal repo exclusion
        included_languages=[Language.PYTHON],
        sort_by=SortCriteria.STARS,
        sort_order=SortOrder.DESCENDING,
        min_repo_size=1,  # 1 KB
        max_repo_size=3000,  # 3 MB
        include_forks=False,
        created_after=datetime.now() - timedelta(days=365*4),  # Repos created in the last 4 years
        pushed_after=datetime.now() - timedelta(days=30),  # Repos pushed to in the last month
        topics=["machine-learning", "data-science"], # this should be confirgurable
        license=None, #any license
        is_public=True
    )

    query = construct_search_query(search_config)
    result = gh.search_repositories(
        query=query, 
        sort=search_config.sort_by.value, 
        order=search_config.sort_order.value
    )

    repos = []
    for repo in result:
        if meets_criteria(search_config, repo):
            repo_dict = create_repo_dict(repo)
            print_repo_details(repo_dict)
            repos.append(repo_dict)
        
        if len(repos) >= limit: 
            break

    return repos

def get_user_repo_query(config: SearchConfig, user_id: str) -> str:
    query_parts = [f"user:{user_id}"]
    
    # Add language filter
    languages = " ".join(f"language:{lang.value}" for lang in config.included_languages)
    query_parts.append(languages)
    
    # Add star filter
    query_parts.append(f"stars:<={config.repo_config.max_stars}")
    
    # Add size filter
    if config.min_repo_size:
        query_parts.append(f"size:>={config.min_repo_size}")
    if config.max_repo_size:
        query_parts.append(f"size:<={config.max_repo_size}")
    
    # Add fork filter
    if not config.include_forks:
        query_parts.append("fork:false")
    
    # Add created date filter
    if config.created_after:
        created_after = config.created_after.strftime("%Y-%m-%d")
        query_parts.append(f"created:>={created_after}")
    
    # Add pushed date filter
    if config.pushed_after:
        pushed_after = config.pushed_after.strftime("%Y-%m-%d")
        query_parts.append(f"pushed:>={pushed_after}")
    
    # Add topics filter
    if config.topics:
        topics = " ".join(f"topic:{topic}" for topic in config.topics)
        query_parts.append(topics)
    
    # Add visibility filter
    if config.is_public is not None:
        query_parts.append("is:public" if config.is_public else "is:private")
    
    return " ".join(query_parts)

def extract_contributors(repos):
    ret : List[NamedUser] = []
    for repo in repos:
        ret.extend(repo['contributors'])
    return ret

# get all repos of user from html_url
def extract_rare_repos(contributors: List[NamedUser]):
    user_repos = dict()
    for contributor in contributors:
        repos: PaginatedList = contributor.get_repos()
        page : List[Repository] = repos.get_page(0)
        user_repos[contributor] = page

    return user_repos

if __name__ == '__main__':
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from analyzer.repo_analyzer import analyze_repository
    from analyzer.code_quality_analyzer import code_quality_analyze
    from extractor.code_extractor import download_py_files
    import json

    limit = 3
    top_files_limit = 3

    init_repos = explore_repos(limit=1)
    user_repos: Dict[NamedUser, List[Repository]] = extract_rare_repos(extract_contributors(init_repos))
    for user,repos in user_repos.items():
        user_dir = os.path.join('users', user.name)
        os.makedirs(user_dir, exist_ok=True)

        # download .py files
        for repo in repos[:limit]:
            repo_path = os.path.join(user_dir, repo.name)
            os.makedirs(repo_path, exist_ok=True)
            if repo.name[0] == '.': 
                print('skipping', repo.name)
                continue
            print(repo.name)
            download_py_files(repo.id, repo_path)

            top_files = analyze_repository(repo_path)[:top_files_limit]
            print(f"Found {len(top_files)} important files in {repo.name}")
            importance_result = [
                {"file": os.path.relpath(file, repo_path), "importance": importance}
                for file, importance in top_files
            ]

            with open(os.path.join(repo_path, 'importance.json'), 'w') as f:
                json.dump(importance_result, f, indent=2)
        
        results = {}
        results = {
            'repo_user': user.avatar_url,
            'repo_url': repo.html_url
        }

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_repo = {
                executor.submit(
                    code_quality_analyze, 
                    repo_path,
                    importance_result
                ): repo.name 
                for repo in repos
            }
            
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    avg_score, analysis_rate, summary = future.result()
                    results[repo] = {
                        "average_score": avg_score,
                        "analysis_rate": analysis_rate,
                        'summary': summary
                    }
                    print(f"Repository {repo}:")
                    print(f"  Average score: {avg_score:.2f}")
                    print(f"  Analysis rate: {analysis_rate:.2f}%")
                except Exception as exc:
                    print(f'{repo} generated an exception: {exc}')

        with open(os.path.join(user_dir,'repo_quality_scores.json'), 'w') as f:
            json.dump(results, f, indent=2)

        print("Analysis complete. Results saved to repo_quality_scores.json")

