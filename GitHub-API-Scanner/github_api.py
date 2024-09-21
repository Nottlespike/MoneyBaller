from github import Github
from typing import List, Dict, Any

class GitHubAPIWrapper:
    def __init__(self, token: str):
        self.github = Github(token)

    def get_user_repos(self):
        return self.github.get_user().get_repos()

    def get_rate_limit(self):
        return self.github.get_rate_limit()

    def get_user_organizations(self, username: str) -> List[Dict[str, Any]]:
        user = self.github.get_user(username)
        return [{'login': org.login, 'name': org.name} for org in user.get_orgs()]