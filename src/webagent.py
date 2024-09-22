import urllib.request
import json
import http.client
import ssl
import os 
from dotenv import load_dotenv

load_dotenv()

def fetch_webpage(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        return f"Error fetching webpage: {str(e)}"

def assess_competency(url):
    webpage_content = fetch_webpage(url)
    
    prompt = f"""You are an expert tech recruiter with deep knowledge of software engineering, web development, and various programming languages and frameworks. You've just been given the HTML content of a personal website. Your task is to thoroughly analyze this content and provide a comprehensive competency assessment of the individual.

Please consider the following aspects in your analysis:
1. Technical skills and programming languages evident from the content
2. Depth and breadth of projects showcased (if any)
3. Full-stack capabilities (frontend, backend, devops)
4. Problem-solving abilities demonstrated through project descriptions or code samples
5. Design sensibilities and user experience considerations
6. Use of modern frameworks, libraries, or technologies
7. Evidence of best practices in coding or software development
8. Any unique or standout skills or projects
9. Areas for potential improvement or skill gaps

Based on your analysis, provide:
1. A detailed assessment of the individual's technical competencies
2. An overall competency level (e.g., junior, mid-level, senior)
3. Potential roles or positions this person might be well-suited for
4. Recommendations for skill improvement or areas to focus on

Here's the webpage content to analyze:

{webpage_content}

Please provide your assessment in a clear, structured format.
"""

    # Claude API endpoint and headers
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": os.getenv("ANTHROPIC_API_KEY"),  # Replace with your actual API key
        "anthropic-version": "2023-06-01"  # Add this required header

    }

    # Request body
    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Make the API request
    conn = http.client.HTTPSConnection("api.anthropic.com", context=context)
    conn.request("POST", "/v1/messages", body=json.dumps(data), headers=headers)

    response = conn.getresponse()
    result = json.loads(response.read().decode())

    conn.close()
    print(result)

    # Extract and return the assistant's message
    return result['content'][0]['text']

# Example usage
if __name__ == "__main__":
    url = "https://minjunes.ai"  # Replace with the actual URL you want to analyze
    assessment = assess_competency(url)
    print(assessment)