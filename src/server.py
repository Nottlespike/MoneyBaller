''''

    user types in profile/repo
    user types in how many candidates they want to search 100? 

    loop.py BFS runs until we get 100

    scores = dict()
    
    for contributor in contributors:
        repo_scores = []
        for repo in get_repo(contributors):
            # we just pass repo to repo analyzer
            for file in repo:
                - score each file -> 
            - compile summary report
            repo_scores.append(summary)
        # get score from all repos

        scores[contributor] = repo_scores

    return scoring results of each contributor

    api service

    - /get_scores query={repo or profile}
    - /chat_repo query={repo}


    # what the user will see:
        - candidate 1 -> summary score
            - repo1 -> repo score
                - file1 -> scores for each file (1 call -> max 10,000 tokens)
            - repo2
'''