import requests
from bs4 import BeautifulSoup

def get_html_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def scrape_github_profile(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    vcard_details = soup.find('ul', class_='vcard-details')
    
    if not vcard_details:
        return None
    
    info = {}
    
    for li in vcard_details.find_all('li'):
        if 'octicon-location' in str(li):
            info['location'] = li.text.strip()
        elif 'octicon-link' in str(li):
            link = li.find('a')
            info['website'] = link.get('href') if link else ''
        
        # Direct parsing for specific social media links
        link = li.find('a')
        if link:
            href = link.get('href', '')
            if 'https://twitter.com/' in href:
                info['twitter'] = href
            elif 'https://www.linkedin.com/' in href:
                info['linkedin'] = href
            elif 'https://twitch.tv/' in href:
                info['twitch'] = href
    
    return info

# Example usage
github_username = "nottlespike"
url = f"https://github.com/{github_username}"

html_content = get_html_content(url)

if html_content:
    result = scrape_github_profile(html_content)
    if result:
        print(f"Scraped information for {github_username}:")
        for key, value in result.items():
            print(f"{key.capitalize()}: {value}")
    else:
        print("No vcard-details found in the provided HTML.")
else:
    print("Failed to fetch HTML content.")