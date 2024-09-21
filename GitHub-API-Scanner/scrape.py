from bs4 import BeautifulSoup
import re
import requests
def extract_collaborator_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the contributors section
    contributors_section = soup.find('a', href=re.compile(r'/graphs/contributors'))
    
    if contributors_section:
        # Find the ul containing the list of contributors
        contributors_list = contributors_section.find_next('ul', class_='list-style-none')
        
        if contributors_list:
            # Find all a tags with href starting with 'https://github.com/'
            collaborator_links = contributors_list.find_all('a', href=lambda href: href and href.startswith('https://github.com/'))
            
            # Extract and return the URLs
            collaborator_urls = [link['href'] for link in collaborator_links]
            
            return collaborator_urls
    
    return []
    
def get_contributors(repo):
    html_content = requests.get(repo).text
    return extract_collaborator_urls(html_content)

html_content = requests.get('https://github.com/ggerganov/llama.cpp')
print(html_content.text)


collaborator_urls = extract_collaborator_urls(html_content.text)
for url in collaborator_urls:
    print(f"https://github.com{url}")