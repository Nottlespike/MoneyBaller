from bs4 import BeautifulSoup

import queue
import requests
import re
import subprocess
import json
import os
from dotenv import load_dotenv

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

def get_contributors(repo):
    # Fetch the content of the file
    try:
        contributors_url = repo['contributors_url']
        response = requests.get(contributors_url)
        response.raise_for_status()  # Raise an exception for bad responses

        # Parse the JSON content
        data = json.loads(response.text)
        contributors = [(user['html_url'], user['contributions']) for user in data]
    
        return contributors
    except Exception as e:
        print(e)
        return []
    

root_profile = 'https://github.com/Nottlespike'
stack = queue.Queue()
added = set()
all_profiles = []
stack.put((root_profile, 0))
max_contributors = 30

while not stack.empty():
    if len(all_profiles) > max_contributors: 
        break
    profile = stack.get()
    all_profiles.append(profile)
    repos = get_repos(profile)
    for repo in repos:
        #print(f'scraping repo {repo}')
        contributors = get_contributors(repo)
        print(f'got {len(contributors)} contributors ')
        for contributor in contributors: 
            if contributor not in added:
                all_profiles.append(contributor)
                stack.put(contributor)
                added.add(contributor)

with open('contributors.txt', 'w') as f:
    for i, (profile,contribs) in enumerate(all_profiles):
        print(f'{profile} {contribs} contribs')
        f.write(profile + '\n')