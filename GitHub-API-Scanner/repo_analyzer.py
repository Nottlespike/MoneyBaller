from datetime import datetime, timedelta
from typing import Dict, List, Any

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