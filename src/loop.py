from bs4 import BeautifulSoup

import queue
import requests
import re
import subprocess
import json
import os
import random
import time
import time

from dotenv import load_dotenv
from collections import deque

load_dotenv()

# The curl command
def get_repos(profile):
    if isinstance(profile, tuple):
        profile = profile[0]
    username = profile.split('/')[-1]
    curl_command = [
        'curl',
        '-H', f"Authorization: {os.getenv('GH_API_KEY')}",
        f'https://api.github.com/users/{username}/repos'
    ]
    print(curl_command)
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        
        # Save the output to a file
        with open('repositories.json', 'w') as f:
            f.write(result.stdout)
        
        # Parse the JSON file
        with open('repositories.json', 'r') as f:
            repositories = json.load(f)
        
        # Now you can work with the parsed JSON data
        repos = []
        for repo in repositories:
            #print(f"Repository: {repo['name']}")
            #print(f"Description: {repo['description']}")
            print(f"URL: {repo['html_url']}")
            print("---")
            # skip files
            if not os.path.splitext(repo['html_url'])[-1]:
                repos.append(repo)
        return repos

    except subprocess.CalledProcessError as e:
        print(f"Error executing curl command: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")

# Load keys from file
with open('../scraping_keys.txt', 'r') as f:
    all_scraping_keys = deque(f.read().splitlines())  # Use deque for efficient rotation

print("Available keys:", all_scraping_keys)

def rotate_key():
    """Rotate the API key to the end of the queue."""
    if all_scraping_keys:
        all_scraping_keys.rotate(-1)
    return all_scraping_keys[0] if all_scraping_keys else None

def get_contributors(url, initial_delay=1, max_delay=60):
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
                rotate_key()  # Rotate to the next key for other errors
            
            if not all_scraping_keys:
                print("All API keys exhausted.")
                return []
        
    return []  # This line will be reached if we exit the while loop (i.e., all keys are exhausted)


root_profile = 'https://github.com/Nottlespike'
stack = queue.Queue()
added = set()
all_profiles = []
stack.put((root_profile, 0))
max_contributors = 30

while not stack.empty():
    profile = stack.get()
    all_profiles.append(profile)
    repos = get_repos(profile)
    for repo in repos:
        #print(f'scraping repo {repo}')
        contributors = get_contributors(repo['contributors_url'])
        print(f'got {len(contributors)} contributors ')
        for contributor in contributors: 
            if len(all_profiles) > max_contributors: 
                break
            if contributor not in added:
                all_profiles.append(contributor)
                stack.put(contributor)
                added.add(contributor)

with open('contributors.txt', 'w') as f:
    for i, (profile,contribs) in enumerate(all_profiles):
        print(f'{profile} {contribs} contribs')
        f.write(profile + '\n')