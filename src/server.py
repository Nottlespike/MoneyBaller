''''
    Create a FastAPI server supporting:
    - GET /scores
        - req: { seed_github_link, num_candidates }
        - res: { scores: dict[contributor_username, repo_scores]}
    - GET /repo
        - req: { github_repo_link }
        - res: { results about the repo itself }

    How /scores would work

    We run the script in `loop.py`, which starting from seed_github_link, does scraping via BFS
    the BFS runs until we get NUM_CANDIDATES candidates. the pseudocode would look like:

    scores = dict()
    for contributor in contributors:
        repo_scores = []
        for repo in get_repo(contributors):
            # we just pass repo to repo analyzer
            for file in repo:
                - score each file
            - compile summary report
            repo_scores.append(summary)
        # get score from all repos
        scores[contributor] = repo_scores
    return scoring results of each contributor


    How /repo would work

    # what the user will see:
        - candidate 1 -> summary score
            - repo1 -> repo score
                - file1 -> scores for each file (1 call -> max 10,000 tokens)
            - repo2
'''

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List
import uvicorn

# Import necessary functions
from loop import calculate_repo_score, fetch_candidates_and_scores

app = FastAPI()

class ScoresRequest(BaseModel):
    seed_github_link: str
    num_candidates: int

class RepoRequest(BaseModel):
    github_repo_link: str

@app.get("/scores")
async def get_scores(
    seed_github_link: str = Query(..., description="The seed GitHub link"),
    num_candidates: int = Query(..., description="Number of candidates")
):
    try:
        # Run BFS scraping to get contributors and their repos
        scores = fetch_candidates_and_scores(seed_github_link, num_candidates)

        return scores
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repo")
async def get_repo_info(
    github_repo_link: str = Query(..., description="The GitHub repo link")
):
    try:
        # Analyze the specified repo
        repo_score = calculate_repo_score(github_repo_link)
        return {"score": repo_score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ... existing code ...