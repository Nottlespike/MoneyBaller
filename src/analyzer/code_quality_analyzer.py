import os
import json
import re
import time
import anthropic
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from anthropic import RateLimitError

# Load environment variables
load_dotenv()

# Initialize Anthropic client
client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

def extract_score(text):
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group())
            return result.get('score', None)
        except json.JSONDecodeError:
            pass
    score_match = re.search(r'score.*?(\d+)', text, re.IGNORECASE)
    return int(score_match.group(1)) if score_match else None

def analyze_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()

    prompt = f"""You are an expert code reviewer. Please analyze the following Python code and rate its quality on a scale from 1 to 10, where 1 is very poor quality and 10 is excellent quality. Consider factors such as readability, efficiency, adherence to PEP 8 style guide, proper use of Python idioms, and overall structure.

Code to analyze:

{content}

Please respond with only a JSON object containing one key: 'score' (an integer from 1 to 10).
"""

    max_retries = 5
    for attempt in range(max_retries):
        print('attempting...')
        try:
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=100,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            score = extract_score(response.content[0].text)
            if score is not None:
                return {"score": score, "analyzed": True}
            else:
                print(f"Failed to extract score for {file_path}. Retrying...")
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limit hit. Waiting for {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Max retries reached for {file_path} due to rate limiting. Skipping.")
                return {"score": None, "analyzed": False}
        except Exception as e:
            print(f"Error analyzing file {file_path}: {str(e)}")
            return {"score": None, "analyzed": False}
    
    print(f"Failed to analyze {file_path} after {max_retries} attempts.")
    return {"score": None, "analyzed": False}

def generate_summary(content):
    prompt = f"""Please provide a concise summary (about 500 tokens) of the following Python codebase:

{content}

Focus on the main functionality, key components, and overall structure of the code.
"""

    try:
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=600,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return "Failed to generate summary."

def code_quality_analyze(repo_path, important_files):
    scores = []
    analyzed_files = 0
    if len(important_files) == 0:
        return 0, 0, 'nothing to analyze, skipping'
    all_content = '' 
    for file_info in important_files:
        file_path = os.path.join(repo_path, file_info['file'])
        print(file_path)
        print(os.path.exists(file_path))
        if os.path.exists(file_path):

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            all_content += content

            result = analyze_file(file_path)
            if result["analyzed"]:
                scores.append(result['score'])
                analyzed_files += 1
                print(f"Analyzed {file_path}: Score {result['score']}")
            else:
                print(f"Failed to analyze {file_path}")
        else:
            print(f"File not found: {file_path}")
    
    summary = generate_summary(all_content)

    if analyzed_files > 0:
        avg_score = sum(scores) / analyzed_files
        analysis_rate = (analyzed_files / len(important_files)) * 100
        return avg_score, analysis_rate, summary
    else:
        return 0, 0, summary

def main():
    repos_dir = os.path.join('data', 'github_repos_python_files')
    
    # Load the file importance data
    with open('repo_file_importance.json', 'r') as f:
        file_importance_data = json.load(f)
    
    results = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_repo = {
            executor.submit(
                code_quality_analyze, 
                os.path.join(repos_dir, repo), 
                file_importance_data[repo]
            ): repo 
            for repo in file_importance_data
        }
        
        for future in as_completed(future_to_repo):
            repo = future_to_repo[future]
            try:
                avg_score, analysis_rate, summary = future.result()
                results[repo] = {
                    "average_score": avg_score,
                    "analysis_rate": analysis_rate,
                    "summary": summary
                }
                print(f"Repository {repo}:")
                print(f"  Average score: {avg_score:.2f}")
                print(f"  Analysis rate: {analysis_rate:.2f}%")
                print(f"  Summary: {summary[:100]}...")  # Print first 100 characters of summary
            except Exception as exc:
                print(f'{repo} generated an exception: {exc}')

    with open('repo_quality_scores.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Analysis complete. Results saved to repo_quality_scores.json")

if __name__ == "__main__":
    main()