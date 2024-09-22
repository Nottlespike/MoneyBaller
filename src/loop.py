from bs4 import BeautifulSoup

from functools import cache
import queue
import requests
import re
import subprocess
import json
import os
import random
import time
from typing import Union, List, Optional, Tuple, Dict, Any

from dotenv import load_dotenv
from collections import deque

load_dotenv()

# The curl command
def get_repos(profile_url: str) -> List[str]:
    """
    Performs web scraping on GitHub repositories and contributors starting from a root profile URL,
    utilizing API keys for access and saving the results to a text file.
    """
    username = profile_url.split('/')[-1]
    curl_command = [
        'curl',
        '-H', f"Authorization: {os.getenv('GH_API_KEY')}",
        f'https://api.github.com/users/{username}/repos'
    ]
    print(f"{curl_command=}")
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)

        # Save the output to a file
        with open('repositories.json', 'w') as f:
            f.write(result.stdout)

        # Parse the JSON file
        with open('repositories.json', 'r') as f:
            repositories = json.load(f)

        # Now you can work with the parsed JSON data
        result_repos = []
        for repo in repositories:
            #print(f"Repository: {repo['name']}")
            #print(f"Description: {repo['description']}")
            print(f"URL: {repo['html_url']}")
            print("---")
            # skip files
            if not os.path.splitext(repo['html_url'])[-1]:
                result_repos.append(repo)
        return result_repos

    except subprocess.CalledProcessError as e:
        print(f"Error executing curl command: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")


def rotate_key(all_scraping_keys) -> Optional[str]:
    """Rotate the API key to the end of the queue."""
    if all_scraping_keys:
        all_scraping_keys.rotate(-1)
    return all_scraping_keys[0] if all_scraping_keys else None


def get_contributors(url: str, all_scraping_keys: deque, initial_delay=1, max_delay=60) -> List[Tuple[str, int]]:
    """
    Retrieves a list of contributors for a given URL using multiple API
    keys with error handling for rate limiting and key exhaustion.
    """
    delay = initial_delay
    while all_scraping_keys:
        current_key = all_scraping_keys[0]
        try:
            response = requests.get(
                url='https://app.scrapingbee.com/api/v1/',
                params={
                    'api_key': current_key,
                    'url': url,
                }
            )
            print(f'Response HTTP Status Code: {response.status_code}')

            # unexpected err
            if response.status_code != 200:
                print(response.text)
                return []
            # Parse the JSON content
            data = json.loads(response.text)
            contributors = [(user['html_url'], user['contributions']) for user in data]
            return contributors

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if response.status_code == 403 or "Credits" in str(e):
                print(f"API key {current_key} exhausted. Removing and rotating to next key.")
                all_scraping_keys.popleft()  # Remove the exhausted key
            elif response.status_code == 429:  # Too Many Requests
                print(f"Rate limited. Waiting for {delay} seconds before retrying...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)  # Exponential backoff with a maximum delay
            else:
                print(f"Unexpected error. Rotating to next key.")
                rotate_key(all_scraping_keys)  # Rotate to the next key for other errors

            if not all_scraping_keys:
                print("All API keys exhausted.")
                return []

    return []  # This line will be reached if we exit the while loop (i.e., all keys are exhausted)


def do_dfs(all_scraping_keys: deque, seed_github_link: str, num_candidates: int) -> Dict[str, Tuple[int, Any]]:
    # Init BFS
    q = queue.Queue()
    q.put((seed_github_link, 0))
    added = set([seed_github_link])   # prevent cycles
    all_profiles = dict()
    num_profiles = 0

    def process_repos_for_profile():
        nonlocal num_profiles

        for repo in repos:
            #print(f'scraping repo {repo}')
            contributors = get_contributors(repo['contributors_url'], all_scraping_keys)
            print(f"repo {repo['full_name']}, got {len(contributors)} contributors")
            for profile_url, contribs in contributors:
                if profile_url not in added:
                    q.put((profile_url, contribs))
                    added.add(profile_url)
                    num_profiles += 1
                    if num_profiles >= num_candidates:
                        return  # stop adding new contributors to queue

    # DFS on the q starting from seed_github_link
    while not q.empty():
        profile_url, num_contribs_to_orig_addition_repo = q.get()
        repos = get_repos(profile_url)

        # Add profile stats
        all_profiles[profile_url] = (num_contribs_to_orig_addition_repo, repos)
        print(f"added {profile_url}, now {len(all_profiles)} profiles")

        if num_profiles >= num_candidates:
            continue  # stop adding new contributors to queue

        process_repos_for_profile()

    return all_profiles


def run_bfs_scraping(seed_github_link: str, num_candidates: int=10) -> Dict[str, Tuple[int, Any]]:
    """
    Performs BFS on GitHub repositories to retrieve contributors' profiles and their contributions,
    using scraping keys and limiting the number of contributors fetched.
    """
    # Load keys from file
    with open('scraping_keys.txt', 'r') as f:
        all_scraping_keys = deque(f.read().splitlines())  # Use deque for efficient rotation
    print("Available keys:", all_scraping_keys)

    all_profiles = do_dfs(all_scraping_keys, seed_github_link, num_candidates)

    with open('contributors.txt', 'w') as f:
        for profile_url, (contribs, repos) in all_profiles.items():
            print(f'{profile_url} has {contribs} contribs')
            f.write(f'{profile_url}, {contribs}, {repos}\n')

    return all_profiles


@cache
def fetch_candidates_and_scores(seed_github_link: str, num_candidates: int=10) -> Dict[str, Tuple[int, Any]]:
    # Run BFS scraping to get contributors and their repos
    all_profiles = run_bfs_scraping(seed_github_link, num_candidates)

    scores = {}
    for profile_url, (contribs, repos) in all_profiles.items():
        repo_scores = {}
        for repo in repos:
            # Analyze each repo
            repo_summary = "REPO_SUMMARY TEST"
            repo_scores[repo['full_name']] = repo_summary
        scores[profile_url] = repo_scores

    return {"scores": scores}


if __name__ == "__main__":
    # run_bfs_scraping('https://github.com/Nottlespike', 3)
    print(fetch_candidates_and_scores('https://github.com/Nottlespike', 3))
