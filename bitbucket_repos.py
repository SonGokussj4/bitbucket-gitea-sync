import os
from dataclasses import dataclass

import niquests
from dotenv import load_dotenv
from niquests.auth import HTTPBasicAuth

from log_config import logger

load_dotenv()

# Bitbucket instance details
BITBUCKET_URL = os.getenv("BITBUCKET_URL", "")
BITBUCKET_PROJECT = os.getenv("BITBUCKET_PROJECT", "")

# Authentication details
BITBUCKET_USERNAME = os.getenv("BITBUCKET_USERNAME", "")
BITBUCKET_PASSWORD = os.getenv("BITBUCKET_PASSWORD", "")
BITBUCKET_TOKEN = os.getenv("BITBUCKET_TOKEN", "")

# API endpoint for listing repositories
BITBUCKET_PROJECTS_API_URL = f"{BITBUCKET_URL}/rest/api/1.0/projects"
BITBUCKET_REPOS_API_URL = f"{BITBUCKET_URL}/rest/api/1.0/projects/{BITBUCKET_PROJECT}/repos"


@dataclass
class Repository:
    name: str
    link: str
    description: str


def list_repositories() -> list[Repository]:
    """
    List all repositories for the specified Bitbucket project, handling pagination.
    """
    auth = HTTPBasicAuth(BITBUCKET_USERNAME, BITBUCKET_PASSWORD)
    repo_list: list[Repository] = []
    start = 0
    is_last_page = False

    # Using Niquests' Session with multiplexing enabled for improved performance
    with niquests.Session(multiplexed=True) as session:
        while not is_last_page:
            response: niquests.Response = session.get(f"{BITBUCKET_REPOS_API_URL}?start={start}", auth=auth, verify=True)
            if response.status_code == 200:
                data = response.json()
                repos = data["values"]
                for repo in repos:
                    repo_info = Repository(
                        name=repo["name"],
                        link=repo["links"]["clone"][0]["href"],
                        description=repo.get("description", ""),
                    )
                    repo_list.append(repo_info)
                    logger.info(f"Repository: {repo_info.name}, Link: {repo_info.link}, Description: {repo_info.description}")

                is_last_page = data["isLastPage"]
                if not is_last_page:
                    start = data["nextPageStart"]
            else:
                logger.error(f"Failed to list repositories: {response.status_code} - {response.text}")
                break

    return repo_list


if __name__ == "__main__":
    repositories = list_repositories()
    logger.info(f"Total repositories found: {len(repositories)}")
